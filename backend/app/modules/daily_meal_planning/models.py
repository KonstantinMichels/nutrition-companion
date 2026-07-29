from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utc_now

if TYPE_CHECKING:
    from app.modules.foods.models import Food, FoodMeasure
    from app.modules.nutrition_assessment.models import Assessment
    from app.modules.profiles.models import Profile
    from app.modules.recipes.models import Recipe


class DailyMealPlan(Base):
    __tablename__ = "daily_meal_plans"
    __table_args__ = (
        Index("ix_daily_plan_owner_date", "owner_profile_id", "plan_date"),
        Index(
            "uq_daily_plan_active_owner_date",
            "owner_profile_id",
            "plan_date",
            unique=True,
            postgresql_where=text("is_archived = false"),
            sqlite_where=text("is_archived = 0"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    owner: Mapped[Profile] = relationship(back_populates="daily_meal_plans")
    assessment: Mapped[Assessment | None] = relationship()
    meals: Mapped[list[Meal]] = relationship(
        back_populates="daily_plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Meal.position",
    )


class Meal(Base):
    __tablename__ = "meals"
    __table_args__ = (
        CheckConstraint("position >= 0", name="meal_nonnegative_position"),
        Index("ix_meal_plan_position", "daily_plan_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    daily_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_meal_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_name: Mapped[str | None] = mapped_column(String(200))
    planned_time: Mapped[time | None] = mapped_column(Time(timezone=False))
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    daily_plan: Mapped[DailyMealPlan] = relationship(back_populates="meals")
    entries: Mapped[list[MealEntry]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MealEntry.position",
    )


class MealEntry(Base):
    __tablename__ = "meal_entries"
    __table_args__ = (
        CheckConstraint("position >= 0", name="entry_nonnegative_position"),
        CheckConstraint(
            "recipe_portion_count IS NULL OR recipe_portion_count > 0",
            name="entry_positive_recipe_portions",
        ),
        CheckConstraint(
            "food_quantity IS NULL OR food_quantity > 0", name="entry_positive_food_quantity"
        ),
        CheckConstraint("entry_type IN ('recipe', 'food')", name="entry_valid_type"),
        CheckConstraint(
            "(entry_type = 'recipe' AND recipe_id IS NOT NULL AND "
            "recipe_portion_count IS NOT NULL AND food_id IS NULL AND food_quantity IS NULL "
            "AND food_unit_code IS NULL AND food_measure_id IS NULL) OR "
            "(entry_type = 'food' AND food_id IS NOT NULL AND food_quantity IS NOT NULL "
            "AND recipe_id IS NULL AND recipe_portion_count IS NULL "
            "AND (food_unit_code IS NOT NULL OR food_measure_id IS NOT NULL))",
            name="entry_source_shape",
        ),
        Index("ix_meal_entry_position", "meal_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meal_id: Mapped[UUID] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_type: Mapped[str] = mapped_column(String(16), nullable=False)
    recipe_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"), index=True
    )
    food_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), index=True
    )
    recipe_portion_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    food_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    food_unit_code: Mapped[str | None] = mapped_column(String(32))
    food_measure_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("food_measures.id", ondelete="RESTRICT")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    meal: Mapped[Meal] = relationship(back_populates="entries")
    recipe: Mapped[Recipe | None] = relationship()
    food: Mapped[Food | None] = relationship()
    food_measure: Mapped[FoodMeasure | None] = relationship()
