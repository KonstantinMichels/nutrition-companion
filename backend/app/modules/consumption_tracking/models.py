from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now

if TYPE_CHECKING:
    from app.modules.daily_meal_planning.models import DailyMealPlan
    from app.modules.foods.models import Food, FoodMeasure
    from app.modules.nutrition_assessment.models import Assessment
    from app.modules.profiles.models import Profile
    from app.modules.recipes.models import Recipe
    from app.modules.training_day_adjustments.models import TrainingDayTargetAdjustment


class ConsumptionDay(Base):
    __tablename__ = "consumption_days"
    __table_args__ = (
        UniqueConstraint(
            "owner_profile_id", "consumption_date", name="uq_consumption_day_owner_date"
        ),
        Index("ix_consumption_day_owner_date", "owner_profile_id", "consumption_date"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consumption_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_daily_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("daily_meal_plans.id", ondelete="SET NULL"), index=True
    )
    assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"), index=True
    )
    training_day_adjustment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("training_day_target_adjustments.id", ondelete="SET NULL"), index=True
    )
    target_basis_source: Mapped[str] = mapped_column(String(40), nullable=False)
    target_basis_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    completeness_attestation: Mapped[str] = mapped_column(
        String(40), nullable=False, default="not_declared"
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalization_operation_id: Mapped[UUID | None] = mapped_column(unique=True)
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    owner: Mapped[Profile] = relationship()
    source_daily_plan: Mapped[DailyMealPlan | None] = relationship()
    assessment: Mapped[Assessment | None] = relationship()
    training_day_adjustment: Mapped[TrainingDayTargetAdjustment | None] = relationship()
    meals: Mapped[list[ConsumptionMeal]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ConsumptionMeal.position",
    )
    outcomes: Mapped[list[PlannedEntryConsumptionOutcome]] = relationship(
        back_populates="day", cascade="all, delete-orphan", passive_deletes=True
    )


class ConsumptionMeal(Base):
    __tablename__ = "consumption_meals"
    __table_args__ = (
        CheckConstraint("position >= 0", name="consumption_meal_position"),
        Index("ix_consumption_meal_day_position", "consumption_day_id", "position"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    consumption_day_id: Mapped[UUID] = mapped_column(
        ForeignKey("consumption_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_name: Mapped[str | None] = mapped_column(String(200))
    consumed_time: Mapped[time | None] = mapped_column(Time(timezone=False))
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    source_plan_meal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meals.id", ondelete="SET NULL"), index=True
    )
    source_plan_meal_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    day: Mapped[ConsumptionDay] = relationship(back_populates="meals")
    entries: Mapped[list[ConsumptionEntry]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ConsumptionEntry.position",
    )


class PlannedEntryConsumptionOutcome(Base):
    __tablename__ = "planned_entry_consumption_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "consumption_day_id", "source_plan_entry_id", name="uq_consumption_outcome_day_entry"
        ),
        UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_consumption_outcome_operation"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    consumption_day_id: Mapped[UUID] = mapped_column(
        ForeignKey("consumption_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_daily_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("daily_meal_plans.id", ondelete="SET NULL")
    )
    source_plan_meal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meals.id", ondelete="SET NULL")
    )
    source_plan_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meal_entries.id", ondelete="SET NULL"), index=True
    )
    source_plan_entry_type_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    source_display_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    planned_quantity_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    planned_unit_snapshot: Mapped[str | None] = mapped_column(String(32))
    planned_recipe_portions_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    source_version_snapshot: Mapped[str | None] = mapped_column(String(80))
    source_plan_entry_updated_at_snapshot: Mapped[str | None] = mapped_column(String(80))
    outcome_type: Mapped[str] = mapped_column(String(32), nullable=False)
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    day: Mapped[ConsumptionDay] = relationship(back_populates="outcomes")
    entries: Mapped[list[ConsumptionEntry]] = relationship(back_populates="outcome")


class ConsumptionEntry(Base):
    __tablename__ = "consumption_entries"
    __table_args__ = (
        CheckConstraint("position >= 0", name="consumption_entry_position"),
        CheckConstraint(
            "entered_quantity IS NULL OR entered_quantity > 0", name="consumption_entry_quantity"
        ),
        CheckConstraint(
            "recipe_portion_count IS NULL OR recipe_portion_count > 0",
            name="consumption_entry_portions",
        ),
        UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_consumption_entry_operation"
        ),
        Index("ix_consumption_entry_meal_position", "consumption_meal_id", "position"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    consumption_meal_id: Mapped[UUID] = mapped_column(
        ForeignKey("consumption_meals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    outcome_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("planned_entry_consumption_outcomes.id", ondelete="CASCADE"), index=True
    )
    entry_type: Mapped[str] = mapped_column(String(24), nullable=False)
    origin_type: Mapped[str] = mapped_column(String(24), nullable=False)
    food_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("foods.id", ondelete="SET NULL"), index=True
    )
    recipe_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL"), index=True
    )
    manual_name: Mapped[str | None] = mapped_column(String(200))
    source_plan_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meal_entries.id", ondelete="SET NULL"), index=True
    )
    source_display_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    source_version_snapshot: Mapped[str | None] = mapped_column(String(80))
    source_metadata_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    entered_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    entered_unit_code: Mapped[str | None] = mapped_column(String(32))
    entered_unit_label: Mapped[str | None] = mapped_column(String(80))
    food_measure_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("food_measures.id", ondelete="SET NULL")
    )
    normalized_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    normalized_unit: Mapped[str | None] = mapped_column(String(8))
    recipe_portion_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    conversion_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nutrient_snapshot_status: Mapped[str] = mapped_column(String(24), nullable=False)
    calculation_rule_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="consumption-snapshot/1.0"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    meal: Mapped[ConsumptionMeal] = relationship(back_populates="entries")
    outcome: Mapped[PlannedEntryConsumptionOutcome | None] = relationship(back_populates="entries")
    food: Mapped[Food | None] = relationship()
    recipe: Mapped[Recipe | None] = relationship()
    food_measure: Mapped[FoodMeasure | None] = relationship()
    nutrient_snapshots: Mapped[list[ConsumptionEntryNutrientSnapshot]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", passive_deletes=True
    )
    recipe_ingredient_snapshots: Mapped[list[ConsumptionRecipeIngredientSnapshot]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ConsumptionRecipeIngredientSnapshot.ingredient_position",
    )


class ConsumptionEntryNutrientSnapshot(Base):
    __tablename__ = "consumption_entry_nutrient_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "consumption_entry_id", "nutrient_code", name="uq_consumption_snapshot_entry_code"
        ),
        Index("ix_consumption_snapshot_code", "nutrient_code"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    consumption_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("consumption_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nutrient_code: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    canonical_unit: Mapped[str] = mapped_column(String(24), nullable=False)
    value_state: Mapped[str] = mapped_column(String(24), nullable=False)
    source_quality: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    entry: Mapped[ConsumptionEntry] = relationship(back_populates="nutrient_snapshots")


class ConsumptionRecipeIngredientSnapshot(Base):
    __tablename__ = "consumption_recipe_ingredient_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "consumption_entry_id",
            "ingredient_position",
            name="uq_consumption_recipe_snapshot_position",
        ),
        Index("ix_consumption_recipe_snapshot_food", "food_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    consumption_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("consumption_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_recipe_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL")
    )
    source_recipe_ingredient_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipe_ingredients.id", ondelete="SET NULL")
    )
    food_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("foods.id", ondelete="SET NULL"), index=True
    )
    food_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    ingredient_position: Mapped[int] = mapped_column(Integer, nullable=False)
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    original_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_quantity_for_logged_portions: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    canonical_unit: Mapped[str | None] = mapped_column(String(8))
    food_measure_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    conversion_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    optional_ingredient: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    normalization_status: Mapped[str] = mapped_column(String(24), nullable=False)
    source_version_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    entry: Mapped[ConsumptionEntry] = relationship(back_populates="recipe_ingredient_snapshots")
