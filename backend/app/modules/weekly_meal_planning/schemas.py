from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator


class WeeklyWarning(BaseModel):
    code: str
    severity: Literal["info", "warning"]
    explanation_de: str
    date: Date | None = None
    nutrient_code: str | None = None
    suggested_action_de: str | None = None


class WeeklyNutrient(BaseModel):
    nutrient_code: str
    display_name_de: str
    category: str
    amount: Decimal | None
    average_per_planned_day: Decimal | None
    unit: str
    planned_day_count: int
    days_with_known_value: int
    days_with_complete_value: int
    coverage_ratio: Decimal | None
    is_complete: bool
    missing_sources: list[dict[str, object]]


class WeeklyTargetComparison(BaseModel):
    nutrient_code: str
    display_name_de: str
    category: str
    target_kind: str | None
    amount: Decimal | None
    average_per_planned_day: Decimal | None
    unit: str
    target_minimum: Decimal | None = None
    target_value: Decimal | None = None
    target_maximum: Decimal | None = None
    target_day_count: int
    missing_target_day_count: int
    relation: str
    comparison_status: str
    remaining_amount: Decimal | None = None
    remaining_kind: str | None = None
    remaining_status: str | None = None
    contribution_percent: Decimal | None = None
    target_basis_status: str
    assessment_ids: list[UUID]
    reference_set_versions: list[str]
    application_rule_set_versions: list[str]
    explanation_de: str
    coverage_ratio: Decimal | None


class WeeklyDay(BaseModel):
    date: Date
    weekday: str
    state: Literal["no_plan", "empty_plan", "planned", "archived_only"]
    plan: dict[str, object] | None
    summary: dict[str, object]
    target_status: dict[str, object]
    warnings: list[WeeklyWarning]
    meals: list[dict[str, object]]


class WeeklyMealPlanResponse(BaseModel):
    week_start: Date
    week_end: Date
    iso_week_number: int
    iso_week_year: int
    days: list[WeeklyDay]
    day_counts: dict[str, int]
    weekly_totals: list[WeeklyNutrient]
    weekly_target_comparison: list[WeeklyTargetComparison]
    quality: dict[str, object]
    warnings: list[WeeklyWarning]
    calculated_at: datetime
    notices: list[str]


class MealTransferRequest(BaseModel):
    source_plan_id: UUID
    source_meal_id: UUID
    target_date: Date
    copy_mode: Literal["new_meal", "append_to_existing_meal"] = "new_meal"
    target_meal_id: UUID | None = None
    assessment_copy_mode: Literal["source", "latest", "none"] = "source"

    @model_validator(mode="after")
    def target_shape(self) -> MealTransferRequest:
        if self.copy_mode == "append_to_existing_meal" and self.target_meal_id is None:
            raise ValueError("target_meal_id required when appending")
        if self.copy_mode == "new_meal" and self.target_meal_id is not None:
            raise ValueError("target_meal_id only allowed when appending")
        return self


class MealTransferResponse(BaseModel):
    operation: Literal["copy", "move"]
    source_plan_id: UUID
    target_plan_id: UUID
    target_meal_id: UUID
    target_date: Date
    message_de: str
