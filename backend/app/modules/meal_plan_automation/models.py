from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now


class AutomationPreferences(Base):
    __tablename__ = "meal_plan_automation_preferences"
    __table_args__ = (
        Index("ix_automation_preferences_owner_default", "owner_profile_id", "is_default"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assessment_selection_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="latest_usable"
    )
    selected_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL")
    )
    generation_scope_default: Mapped[str] = mapped_column(
        String(24), nullable=False, default="single_day"
    )
    pantry_preference: Mapped[str] = mapped_column(
        String(32), nullable=False, default="prefer_available"
    )
    shopping_effort_preference: Mapped[str] = mapped_column(
        String(40), nullable=False, default="prefer_fewer_missing_items"
    )
    maximum_recipe_repetitions_per_week: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )
    minimum_days_between_same_recipe: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    maximum_preparation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    allow_incomplete_basic_nutrition: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allow_archived_recipe_candidates: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    include_optional_recipe_ingredients: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    enabled_recipe_tag_codes: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list
    )
    excluded_recipe_tag_codes: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list
    )
    excluded_recipe_ids: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list
    )
    scoring_weights: Mapped[dict[str, str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    optimizer_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_generation_engine: Mapped[str] = mapped_column(
        String(40), nullable=False, default="optimizer_strict"
    )
    solver_time_limit_day_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    solver_time_limit_week_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    solver_relative_gap_limit: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0.02")
    )
    solver_candidate_limit_per_slot: Mapped[int] = mapped_column(
        Integer, nullable=False, default=40
    )
    maximum_recipe_repetitions_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )
    strict_energy_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strict_protein_minimum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strict_fiber_minimum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strict_fat_range: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strict_saturated_fat_maximum: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    strict_daily_preparation_time: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    maximum_daily_preparation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    maximum_weekly_unique_shopping_items: Mapped[int | None] = mapped_column(Integer)
    constraint_relaxation_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    relaxable_constraint_priorities: Mapped[dict[str, int]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    objective_weights: Mapped[dict[str, str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    meal_prep_preference: Mapped[str] = mapped_column(String(24), nullable=False, default="neutral")
    compare_with_greedy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    slots: Mapped[list[AutomationMealSlot]] = relationship(
        back_populates="preferences",
        cascade="all, delete-orphan",
        order_by="AutomationMealSlot.position",
    )


class AutomationMealSlot(Base):
    __tablename__ = "automation_meal_slot_templates"
    __table_args__ = (
        Index("ix_automation_slot_preferences_position", "automation_preferences_id", "position"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    automation_preferences_id: Mapped[UUID] = mapped_column(
        ForeignKey("meal_plan_automation_preferences.id", ondelete="CASCADE"), nullable=False
    )
    slot_code: Mapped[str] = mapped_column(String(48), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_name: Mapped[str | None] = mapped_column(String(200))
    default_time: Mapped[time | None] = mapped_column(Time)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_recipe_tag_codes: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list
    )
    excluded_recipe_tag_codes: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list
    )
    target_energy_share_min: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    target_energy_share_max: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    minimum_protein_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    maximum_preparation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    portion_minimum: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.5")
    )
    portion_maximum: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("2")
    )
    portion_step: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.25")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    preferences: Mapped[AutomationPreferences] = relationship(back_populates="slots")


class AutomationApplication(Base):
    __tablename__ = "meal_plan_automation_applications"
    __table_args__ = (
        UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_automation_application_operation"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(24), nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    automation_preferences_id: Mapped[UUID] = mapped_column(
        ForeignKey("meal_plan_automation_preferences.id", ondelete="RESTRICT"), nullable=False
    )
    assessment_ids: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    applied_references: Mapped[list[dict[str, str]]] = mapped_column(JSON_DOCUMENT, nullable=False)
    applied_slot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    generation_engine: Mapped[str] = mapped_column(String(40), nullable=False, default="greedy")
    solver_status: Mapped[str | None] = mapped_column(String(40))
    solver_version: Mapped[str | None] = mapped_column(String(40))
    objective_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 6))
    relative_gap: Mapped[Decimal | None] = mapped_column(Numeric(12, 8))
    relaxation_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    relaxation_summary: Mapped[list[dict[str, str]]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list
    )
    objective_summary: Mapped[list[dict[str, str]]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list
    )
    greedy_comparison_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
