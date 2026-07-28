from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.foods.models import Food


def get_food(session: Session, profile_id: UUID, food_id: UUID) -> Food | None:
    return session.scalar(
        select(Food)
        .where(Food.id == food_id, Food.owner_profile_id == profile_id)
        .options(selectinload(Food.nutrients), selectinload(Food.measures))
    )


def list_foods(
    session: Session,
    profile_id: UUID,
    *,
    query: str | None,
    category: str | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> tuple[list[Food], int]:
    criteria = [Food.owner_profile_id == profile_id]
    if not include_archived:
        criteria.append(Food.is_archived.is_(False))
    if category:
        criteria.append(Food.category_code == category)
    if query:
        pattern = f"%{query.strip().casefold()}%"
        criteria.append(
            or_(
                func.lower(Food.name).like(pattern),
                func.lower(func.coalesce(Food.brand, "")).like(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(Food).where(*criteria)) or 0
    items = list(
        session.scalars(
            select(Food)
            .where(*criteria)
            .options(selectinload(Food.nutrients), selectinload(Food.measures))
            .order_by(Food.normalized_name, Food.normalized_brand)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def duplicates(
    session: Session, profile_id: UUID, name: str, brand: str | None, exclude_id: UUID | None = None
) -> list[Food]:
    criteria = [
        Food.owner_profile_id == profile_id,
        Food.normalized_name == name.casefold(),
        Food.normalized_brand == ((brand or "").casefold() or None),
    ]
    if exclude_id:
        criteria.append(Food.id != exclude_id)
    return list(
        session.scalars(
            select(Food)
            .where(*criteria)
            .options(selectinload(Food.nutrients), selectinload(Food.measures))
        )
    )


def by_external_id(
    session: Session, profile_id: UUID, source_type: str, external_id: str
) -> Food | None:
    return session.scalar(
        select(Food)
        .where(
            Food.owner_profile_id == profile_id,
            Food.source_type == source_type,
            Food.source_external_id == external_id,
        )
        .options(selectinload(Food.nutrients), selectinload(Food.measures))
    )
