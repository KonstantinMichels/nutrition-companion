from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.foods.models import Food
from app.modules.recipes.models import Recipe, RecipeIngredient

LOAD = (
    selectinload(Recipe.ingredients)
    .selectinload(RecipeIngredient.food)
    .selectinload(Food.nutrients),
    selectinload(Recipe.ingredients)
    .selectinload(RecipeIngredient.food)
    .selectinload(Food.measures),
    selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_measure),
    selectinload(Recipe.steps),
)


def get(session: Session, profile_id: UUID, recipe_id: UUID) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_profile_id == profile_id)
        .options(*LOAD)
    )


def list_recipes(
    session: Session,
    profile_id: UUID,
    *,
    query: str | None,
    tag: str | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> tuple[list[Recipe], int]:
    criteria = [Recipe.owner_profile_id == profile_id]
    if not include_archived:
        criteria.append(Recipe.is_archived.is_(False))
    if query:
        pattern = f"%{query.strip().casefold()}%"
        criteria.append(
            or_(
                func.lower(Recipe.name).like(pattern),
                func.lower(func.coalesce(Recipe.description, "")).like(pattern),
            )
        )
    if tag:
        criteria.append(Recipe.tags.contains([tag]))
    total = session.scalar(select(func.count()).select_from(Recipe).where(*criteria)) or 0
    items = list(
        session.scalars(
            select(Recipe)
            .where(*criteria)
            .options(*LOAD)
            .order_by(Recipe.updated_at.desc(), Recipe.normalized_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def duplicates(
    session: Session, profile_id: UUID, normalized_name: str, exclude_id: UUID | None = None
) -> list[Recipe]:
    criteria = [Recipe.owner_profile_id == profile_id, Recipe.normalized_name == normalized_name]
    if exclude_id:
        criteria.append(Recipe.id != exclude_id)
    return list(session.scalars(select(Recipe).where(*criteria)))
