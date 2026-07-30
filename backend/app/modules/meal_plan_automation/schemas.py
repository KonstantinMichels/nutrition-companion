from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

DEFAULT_WEIGHTS = {
    k: Decimal(v)
    for k, v in {
        "meal_slot_fit": "1",
        "nutrition_target_fit": "2",
        "pantry_availability": "1",
        "shopping_effort": "0.5",
        "preparation_time_fit": "0.5",
        "recipe_variety": "1",
        "recipe_preference": "0.5",
        "data_quality": "1",
    }.items()
}
DEFAULT_OBJECTIVE_WEIGHTS = {
    key: Decimal(value)
    for key, value in {
        "nutrition_fit": "3",
        "pantry_usage": "2",
        "shopping_effort": "2",
        "preparation_time": "1",
        "variety": "2",
        "meal_prep": "1",
        "recipe_preference": "1",
        "data_quality": "1",
    }.items()
}


class SlotWrite(BaseModel):
    slot_code: str = Field(min_length=1, max_length=48)
    meal_type: str = Field(min_length=1, max_length=32)
    custom_name: str | None = None
    default_time: time | None = None
    position: int = Field(ge=0)
    is_enabled: bool = True
    allowed_recipe_tag_codes: list[str] = Field(default_factory=list)
    excluded_recipe_tag_codes: list[str] = Field(default_factory=list)
    target_energy_share_min: Decimal | None = Field(None, ge=0, le=1)
    target_energy_share_max: Decimal | None = Field(None, ge=0, le=1)
    minimum_protein_g: Decimal | None = Field(None, ge=0)
    maximum_preparation_time_minutes: int | None = Field(None, ge=0)
    portion_minimum: Decimal = Field(Decimal("0.5"), gt=0)
    portion_maximum: Decimal = Field(Decimal("2"), gt=0)
    portion_step: Decimal = Field(Decimal("0.25"), gt=0)

    @model_validator(mode="after")
    def range(self) -> SlotWrite:
        if self.portion_maximum < self.portion_minimum:
            raise ValueError("Ungültiger Portionsbereich.")
        return self


class PreferencesWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    is_default: bool = False
    assessment_selection_mode: Literal["latest_usable", "explicit", "per_existing_daily_plan"] = (
        "latest_usable"
    )
    selected_assessment_id: UUID | None = None
    generation_scope_default: Literal["single_day", "iso_week"] = "single_day"
    pantry_preference: Literal["ignore", "prefer_available", "require_fully_available"] = (
        "prefer_available"
    )
    shopping_effort_preference: Literal[
        "ignore", "prefer_fewer_missing_items", "prefer_lower_missing_quantity"
    ] = "prefer_fewer_missing_items"
    maximum_recipe_repetitions_per_week: int = Field(2, ge=1, le=21)
    minimum_days_between_same_recipe: int = Field(1, ge=0, le=7)
    maximum_preparation_time_minutes: int | None = Field(None, ge=0)
    allow_incomplete_basic_nutrition: bool = False
    allow_archived_recipe_candidates: bool = False
    include_optional_recipe_ingredients: bool = False
    enabled_recipe_tag_codes: list[str] = Field(default_factory=list)
    excluded_recipe_tag_codes: list[str] = Field(default_factory=list)
    excluded_recipe_ids: list[UUID] = Field(default_factory=list)
    scoring_weights: dict[str, Decimal] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    optimizer_enabled: bool = True
    default_generation_engine: Literal[
        "greedy", "optimizer_strict", "optimizer_explainable_relaxation"
    ] = "optimizer_strict"
    solver_time_limit_day_seconds: int = Field(5, ge=1, le=15)
    solver_time_limit_week_seconds: int = Field(20, ge=5, le=60)
    solver_relative_gap_limit: Decimal = Field(Decimal("0.02"), ge=0, le=Decimal("0.25"))
    solver_candidate_limit_per_slot: int = Field(40, ge=5, le=80)
    maximum_recipe_repetitions_per_day: int = Field(2, ge=1, le=8)
    strict_energy_target: bool = False
    strict_protein_minimum: bool = False
    strict_fiber_minimum: bool = False
    strict_fat_range: bool = False
    strict_saturated_fat_maximum: bool = False
    strict_daily_preparation_time: bool = False
    maximum_daily_preparation_time_minutes: int | None = Field(None, ge=0, le=1440)
    maximum_weekly_unique_shopping_items: int | None = Field(None, ge=0, le=200)
    constraint_relaxation_enabled: bool = False
    relaxable_constraint_priorities: dict[str, int] = Field(default_factory=dict)
    objective_weights: dict[str, Decimal] = Field(
        default_factory=lambda: dict(DEFAULT_OBJECTIVE_WEIGHTS)
    )
    meal_prep_preference: Literal["neutral", "prefer_reuse", "prefer_variety"] = "neutral"
    compare_with_greedy: bool = True
    slots: list[SlotWrite] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid(self) -> PreferencesWrite:
        if self.assessment_selection_mode == "explicit" and self.selected_assessment_id is None:
            raise ValueError("Assessment erforderlich.")
        if any(
            v < 0 or v > 10
            for v in (*self.scoring_weights.values(), *self.objective_weights.values())
        ):
            raise ValueError("Gewichte müssen zwischen 0 und 10 liegen.")
        return self


class GenerateRequest(BaseModel):
    preferences_id: UUID
    scope: Literal["single_day", "iso_week"]
    plan_date: date | None = None
    anchor_date: date | None = None
    existing_plan_mode: Literal[
        "empty_days_only", "empty_meal_slots_only", "draft_all_without_applying"
    ] = "empty_meal_slots_only"
    recipe_overrides: dict[str, UUID] = Field(default_factory=dict)
    portion_overrides: dict[str, Decimal] = Field(default_factory=dict)
    locked_slot_keys: list[str] = Field(default_factory=list)
    removed_slot_keys: list[str] = Field(default_factory=list)
    generation_engine: (
        Literal["greedy", "optimizer_strict", "optimizer_explainable_relaxation"] | None
    ) = None
    reoptimization_scope: Literal["slot", "day", "unlocked", "all"] = "all"
    reoptimization_slot_key: str | None = None
    relaxed_draft_confirmed: bool = False
    training_adjustment_mode: Literal["ignore", "active_by_date", "linked_daily_plans"] = (
        "active_by_date"
    )


class ApplyRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str
    generation: GenerateRequest
    selected_slot_keys: list[str] = Field(default_factory=list)
    create_missing_plans: bool = False
    application_mode: Literal["all_or_nothing", "apply_non_conflicting"] = "all_or_nothing"
    relaxation_confirmed: bool = False
