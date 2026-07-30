from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.daily_meal_planning.enums import EntryType, MealType


class MealEntryWrite(BaseModel):
    entry_type: EntryType
    recipe_id: UUID | None = None
    food_id: UUID | None = None
    recipe_portion_count: Decimal | None = Field(default=None, gt=0, le=100)
    food_quantity: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    food_unit_code: str | None = Field(default=None, max_length=32)
    food_measure_id: UUID | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def source_shape(self) -> MealEntryWrite:
        if self.entry_type == EntryType.RECIPE:
            if self.recipe_id is None or self.recipe_portion_count is None:
                raise ValueError("recipe source and portion count required")
            if any((self.food_id, self.food_quantity, self.food_unit_code, self.food_measure_id)):
                raise ValueError("food fields not allowed for recipe entry")
        else:
            if self.food_id is None or self.food_quantity is None:
                raise ValueError("food source and quantity required")
            if self.food_unit_code is None and self.food_measure_id is None:
                raise ValueError("food unit or measure required")
            if self.recipe_id is not None or self.recipe_portion_count is not None:
                raise ValueError("recipe fields not allowed for food entry")
        return self


class MealWrite(BaseModel):
    meal_type: MealType
    custom_name: str | None = Field(default=None, max_length=200)
    planned_time: time | None = None
    notes: str | None = Field(default=None, max_length=4000)
    entries: list[MealEntryWrite] = Field(default_factory=list, max_length=200)

    @field_validator("custom_name", "notes")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class DailyPlanWrite(BaseModel):
    plan_date: date
    assessment_id: UUID | None = None
    use_latest_assessment: bool = True
    name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    meals: list[MealWrite] = Field(default_factory=list, max_length=30)

    @field_validator("name", "notes")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class DuplicatePlanRequest(BaseModel):
    target_date: date
    copy_assessment: bool = True


class WarningResponse(BaseModel):
    code: str
    severity: Literal["info", "warning"]
    explanation_de: str
    meal_id: UUID | None = None
    entry_id: UUID | None = None
    nutrient_code: str | None = None
    suggested_action_de: str | None = None


class MissingSourceResponse(BaseModel):
    meal_name: str
    entry_name: str
    source_name: str


class NutrientTotalResponse(BaseModel):
    nutrient_code: str
    display_name_de: str
    category: str
    amount: Decimal | None
    unit: str
    known_component_count: int
    relevant_component_count: int
    coverage_ratio: Decimal | None
    is_complete: bool
    missing_sources: list[MissingSourceResponse]


class EntryCalculationResponse(BaseModel):
    id: UUID | None
    position: int
    entry_type: EntryType
    source_id: UUID
    source_name: str
    source_brand: str | None = None
    is_archived: bool
    recipe_portion_count: Decimal | None = None
    food_quantity: Decimal | None = None
    food_unit_code: str | None = None
    food_measure_id: UUID | None = None
    normalized_quantity: Decimal | None = None
    normalized_unit: str | None = None
    conversion_is_estimated: bool = False
    note: str | None = None
    nutrient_totals: list[NutrientTotalResponse]
    warnings: list[WarningResponse]


class MealCalculationResponse(BaseModel):
    id: UUID | None
    position: int
    meal_type: MealType
    meal_name: str
    planned_time: time | None
    notes: str | None
    entry_count: int
    entries: list[EntryCalculationResponse]
    nutrient_totals: list[NutrientTotalResponse]
    basic_nutrition_complete: bool
    warnings: list[WarningResponse]


class TargetComparisonItemResponse(BaseModel):
    nutrient_code: str
    display_name_de: str
    category: str
    target_kind: str
    amount: Decimal | None
    unit: str
    target_minimum: Decimal | None
    target_value: Decimal | None
    target_maximum: Decimal | None
    target_unit: str
    relation: str
    comparison_status: str
    contribution_percent: Decimal | None
    contribution_to_min_percent: Decimal | None
    contribution_to_max_percent: Decimal | None
    remaining_amount: Decimal | None
    remaining_kind: str | None
    remaining_status: str | None
    explanation_de: str
    coverage_ratio: Decimal | None


class AssessmentSummaryResponse(BaseModel):
    id: UUID
    calculated_at: datetime
    goal_type: str
    reference_set_version: str
    application_rule_set_version: str


class QualitySummaryResponse(BaseModel):
    meal_count: int
    entry_count: int
    recipe_entry_count: int
    food_entry_count: int
    normalized_entry_count: int
    estimated_conversion_count: int
    archived_recipe_count: int
    archived_food_count: int
    basic_nutrition_complete: bool
    micronutrient_coverage_level: str
    quality_level: Literal["empty", "incomplete", "basic_complete", "extended"]


class PlanMetadataResponse(BaseModel):
    id: UUID | None
    plan_date: date
    name: str | None
    notes: str | None
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


class DailyPlanResponse(BaseModel):
    plan: PlanMetadataResponse
    assessment: AssessmentSummaryResponse | None
    meals: list[MealCalculationResponse]
    daily_totals: list[NutrientTotalResponse]
    target_comparison: list[TargetComparisonItemResponse]
    quality: QualitySummaryResponse
    warnings: list[WarningResponse]
    calculated_at: datetime
    notices: list[str]
    target_basis: dict[str, object]


class DailyPlanListItem(BaseModel):
    id: UUID
    plan_date: date
    name: str | None
    is_archived: bool
    meal_count: int
    entry_count: int
    assessment_id: UUID | None
    updated_at: datetime


class DailyPlanListResponse(BaseModel):
    items: list[DailyPlanListItem]
    page: int
    page_size: int
    total: int


class ArchivePlanResponse(BaseModel):
    id: UUID
    archived: bool
    message_de: str
