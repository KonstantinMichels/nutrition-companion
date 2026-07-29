from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.modules.recipes.enums import RECIPE_TAGS


class IngredientWrite(BaseModel):
    food_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_type: Literal["base", "measure", "custom_measure"] = "base"
    unit_code: str = Field(min_length=1, max_length=32)
    food_measure_id: UUID | None = None
    equivalent_quantity: Decimal | None = Field(default=None, gt=0)
    equivalent_unit: Literal["g", "ml"] | None = None
    preparation_note: str | None = Field(default=None, max_length=500)
    is_optional: bool = False

    @model_validator(mode="after")
    def measure_requirements(self) -> IngredientWrite:
        if self.unit_type == "measure" and self.food_measure_id is None:
            raise ValueError("measure id required")
        if self.unit_type == "custom_measure" and (
            self.equivalent_quantity is None or self.equivalent_unit is None
        ):
            raise ValueError("custom measure equivalent required")
        if self.unit_type == "base" and self.unit_code not in {"g", "ml"}:
            raise ValueError("base unit must be g or ml")
        return self


class StepWrite(BaseModel):
    instruction: str = Field(min_length=1, max_length=4000)
    optional_duration_minutes: int | None = Field(default=None, ge=0, le=1440)

    @field_validator("instruction")
    @classmethod
    def clean_instruction(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("instruction required")
        return value


class RecipeWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    servings: Decimal = Field(gt=0, le=1000)
    preparation_time_minutes: int | None = Field(default=None, ge=0, le=10080)
    cooking_time_minutes: int | None = Field(default=None, ge=0, le=10080)
    resting_time_minutes: int | None = Field(default=None, ge=0, le=10080)
    finished_weight_g: Decimal | None = Field(default=None, gt=0)
    source_url: HttpUrl | None = None
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    ingredients: list[IngredientWrite] = Field(min_length=1, max_length=200)
    steps: list[StepWrite] = Field(default_factory=list, max_length=100)
    confirm_duplicate: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("name required")
        return value

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, value: list[str]) -> list[str]:
        tags = list(dict.fromkeys(item.strip().casefold() for item in value))
        if any(tag not in RECIPE_TAGS for tag in tags):
            raise ValueError("unknown recipe tag")
        return tags


class MissingIngredientResponse(BaseModel):
    ingredient_id: UUID
    food_id: UUID
    food_name: str


class NutrientCoverageResponse(BaseModel):
    nutrient_code: str
    display_name_de: str
    amount_total: Decimal
    amount_per_serving: Decimal
    amount_per_100g: Decimal | None
    unit: str
    known_ingredient_count: int
    relevant_ingredient_count: int
    coverage_ratio: Decimal
    is_complete: bool
    includes_derived_input: bool
    missing_ingredients: list[MissingIngredientResponse]


class WeightResponse(BaseModel):
    status: Literal["finished_weight", "theoretical_complete", "unavailable"]
    weight_g: Decimal | None
    theoretical_weight_g: Decimal
    coverage_ratio: Decimal


class QualityResponse(BaseModel):
    ingredient_count: int
    normalized_ingredient_count: int
    estimated_conversion_count: int
    archived_food_count: int
    basic_nutrition_complete: bool
    micronutrient_coverage_level: Literal["none", "partial", "complete"]
    quality_level: Literal["incomplete", "basic_complete", "extended"]
    warnings: list[str]


class IngredientResponse(BaseModel):
    id: UUID
    position: int
    food_id: UUID
    food_name: str
    food_brand: str | None
    food_is_archived: bool
    quantity: Decimal
    unit_type: str
    unit_code: str
    unit_name: str
    food_measure_id: UUID | None
    equivalent_quantity: Decimal | None
    equivalent_unit: str | None
    normalized_quantity: Decimal
    normalized_unit: str
    conversion_source: str
    conversion_is_estimated: bool
    preparation_note: str | None
    is_optional: bool


class StepResponse(BaseModel):
    id: UUID
    position: int
    instruction: str
    optional_duration_minutes: int | None


class RecipeResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    servings: Decimal
    preparation_time_minutes: int | None
    cooking_time_minutes: int | None
    resting_time_minutes: int | None
    finished_weight_g: Decimal | None
    source_type: str
    source_name: str | None
    source_url: str | None
    notes: str | None
    tags: list[str]
    tag_labels: list[str]
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    ingredients: list[IngredientResponse]
    steps: list[StepResponse]
    nutrients: list[NutrientCoverageResponse]
    weight: WeightResponse
    quality: QualityResponse


class RecipeListResponse(BaseModel):
    items: list[RecipeResponse]
    page: int
    page_size: int
    total: int


class ScaleIngredientResponse(BaseModel):
    ingredient_id: UUID
    food_name: str
    quantity: Decimal
    unit_code: str


class ScaleResponse(BaseModel):
    base_servings: Decimal
    desired_servings: Decimal
    scaling_factor: Decimal
    ingredients: list[ScaleIngredientResponse]


class ArchiveResponse(BaseModel):
    id: UUID
    archived: bool
    message_de: str


class PermanentDeleteResponse(BaseModel):
    id: UUID
    deleted: bool
    message_de: str
