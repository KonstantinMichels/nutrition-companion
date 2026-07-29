from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ComparableAssessment(BaseModel):
    id: UUID
    calculated_at: datetime
    goal_type: str
    supported_scope_status: str
    energy_target_summary: str | None
    reference_set_version: str
    usable_for_comparison: bool
    unavailable_reason_de: str | None


class ComparableAssessmentsResponse(BaseModel):
    items: list[ComparableAssessment]
    latest_usable_assessment_id: UUID | None


class MissingIngredient(BaseModel):
    ingredient_id: UUID
    food_id: UUID
    food_name: str


class ComparisonItem(BaseModel):
    nutrient_code: str
    display_name_de: str
    category: str
    selected_amount: Decimal | None
    amount_per_serving: Decimal | None
    unit: str
    target_kind: str
    target_minimum: Decimal | None
    target_value: Decimal | None
    target_maximum: Decimal | None
    target_unit: str
    contribution_to_min_percent: Decimal | None
    contribution_percent: Decimal | None
    contribution_to_max_percent: Decimal | None
    relation: str
    comparison_status: Literal["complete", "partial", "unavailable"]
    coverage_ratio: Decimal
    known_ingredient_count: int
    relevant_ingredient_count: int
    missing_ingredients: list[MissingIngredient]
    explanation: str
    formula_de: str | None
    limitations: list[str]


class ComparisonGroup(BaseModel):
    code: str
    display_name_de: str
    items: list[ComparisonItem]


class ComparisonRecipe(BaseModel):
    id: UUID
    name: str
    updated_at: datetime
    base_servings: Decimal


class ComparisonAssessment(BaseModel):
    id: UUID
    calculated_at: datetime
    goal_type: str
    reference_set_version: str
    application_rule_set_version: str


class ComparisonSummary(BaseModel):
    comparable_target_count: int
    complete_comparison_count: int
    partial_comparison_count: int
    unavailable_comparison_count: int
    has_incomplete_basic_nutrition: bool
    has_exceeded_maximum: bool


class TargetComparisonResponse(BaseModel):
    recipe: ComparisonRecipe
    assessment: ComparisonAssessment
    portion_count: Decimal
    calculated_at: datetime
    groups: list[ComparisonGroup]
    summary: ComparisonSummary
    notices: list[str]
