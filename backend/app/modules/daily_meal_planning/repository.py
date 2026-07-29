from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.daily_meal_planning.models import DailyMealPlan, Meal, MealEntry
from app.modules.foods.models import Food
from app.modules.nutrition_assessment.models import Assessment
from app.modules.recipes.models import Recipe, RecipeIngredient

LOAD = (
    selectinload(DailyMealPlan.meals)
    .selectinload(Meal.entries)
    .selectinload(MealEntry.recipe)
    .selectinload(Recipe.ingredients)
    .selectinload(RecipeIngredient.food)
    .selectinload(Food.nutrients),
    selectinload(DailyMealPlan.meals)
    .selectinload(Meal.entries)
    .selectinload(MealEntry.recipe)
    .selectinload(Recipe.ingredients)
    .selectinload(RecipeIngredient.food)
    .selectinload(Food.measures),
    selectinload(DailyMealPlan.meals)
    .selectinload(Meal.entries)
    .selectinload(MealEntry.recipe)
    .selectinload(Recipe.steps),
    selectinload(DailyMealPlan.meals)
    .selectinload(Meal.entries)
    .selectinload(MealEntry.food)
    .selectinload(Food.nutrients),
    selectinload(DailyMealPlan.meals)
    .selectinload(Meal.entries)
    .selectinload(MealEntry.food)
    .selectinload(Food.measures),
    selectinload(DailyMealPlan.meals)
    .selectinload(Meal.entries)
    .selectinload(MealEntry.food_measure),
    selectinload(DailyMealPlan.assessment).selectinload(Assessment.metrics),
)


def get(session: Session, profile_id: UUID, plan_id: UUID) -> DailyMealPlan | None:
    return session.scalar(
        select(DailyMealPlan)
        .where(DailyMealPlan.id == plan_id, DailyMealPlan.owner_profile_id == profile_id)
        .options(*LOAD)
    )


def by_date(
    session: Session, profile_id: UUID, plan_date: date, *, archived: bool = False
) -> DailyMealPlan | None:
    return session.scalar(
        select(DailyMealPlan)
        .where(
            DailyMealPlan.owner_profile_id == profile_id,
            DailyMealPlan.plan_date == plan_date,
            DailyMealPlan.is_archived.is_(archived),
        )
        .options(*LOAD)
        .order_by(DailyMealPlan.updated_at.desc())
        .limit(1)
    )


def list_plans(
    session: Session,
    profile_id: UUID,
    *,
    date_from: date | None,
    date_to: date | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> tuple[list[DailyMealPlan], int]:
    criteria = [DailyMealPlan.owner_profile_id == profile_id]
    if date_from is not None:
        criteria.append(DailyMealPlan.plan_date >= date_from)
    if date_to is not None:
        criteria.append(DailyMealPlan.plan_date <= date_to)
    if not include_archived:
        criteria.append(DailyMealPlan.is_archived.is_(False))
    total = session.scalar(select(func.count()).select_from(DailyMealPlan).where(*criteria)) or 0
    items = list(
        session.scalars(
            select(DailyMealPlan)
            .where(*criteria)
            .options(selectinload(DailyMealPlan.meals).selectinload(Meal.entries))
            .order_by(DailyMealPlan.plan_date.desc(), DailyMealPlan.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def in_date_range(
    session: Session, profile_id: UUID, date_from: date, date_to: date
) -> list[DailyMealPlan]:
    """Batch-load complete calculation inputs for a derived calendar range."""
    return list(
        session.scalars(
            select(DailyMealPlan)
            .where(
                DailyMealPlan.owner_profile_id == profile_id,
                DailyMealPlan.plan_date >= date_from,
                DailyMealPlan.plan_date <= date_to,
            )
            .options(*LOAD)
            .order_by(DailyMealPlan.plan_date, DailyMealPlan.updated_at.desc())
        ).unique()
    )
