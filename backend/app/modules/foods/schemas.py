from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NutrientCatalogResponse(BaseModel):
    code: str
    display_name_de: str
    technical_name_en: str
    category: str
    canonical_unit: str
    display_order: int
    basic_form: bool
    optional: bool
    plausibility_max: Decimal | None
    active: bool


class NutrientInput(BaseModel):
    nutrient_code: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)
    source_note: str | None = Field(default=None, max_length=500)
    is_estimated: bool = False

    @field_validator("amount")
    @classmethod
    def finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("finite decimal required")
        return value


class MeasureInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unit_code: Literal["piece", "serving", "slice", "teaspoon", "tablespoon"]
    equivalent_quantity: Decimal = Field(gt=0)
    equivalent_unit: Literal["g", "ml"]
    is_estimated: bool = False
    note: str | None = Field(default=None, max_length=500)


class FoodWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category_code: str | None = Field(default=None, max_length=48)
    reference_quantity: Decimal = Decimal(100)
    reference_unit: Literal["g", "ml"]
    density_g_per_ml: Decimal | None = Field(default=None, gt=0)
    nutrients: list[NutrientInput] = Field(default_factory=list)
    measures: list[MeasureInput] = Field(default_factory=list)
    confirm_incomplete: bool = False
    confirm_duplicate: bool = False
    confirm_reference_change: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("name required")
        return value

    @field_validator("brand", "description")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def reference_is_100(self) -> FoodWrite:
        if self.reference_quantity != 100:
            raise ValueError("reference quantity must equal 100")
        return self


class NutrientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nutrient_code: str
    display_name_de: str
    amount: Decimal
    unit: str
    value_source: str
    source_note: str | None
    is_estimated: bool
    is_derived: bool = False


class MeasureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    quantity: Decimal
    unit_code: str
    equivalent_quantity: Decimal
    equivalent_unit: str
    is_estimated: bool
    source_type: str
    note: str | None


class QualityResponse(BaseModel):
    basic_nutrition_complete: bool
    known_nutrient_count: int
    available_micronutrient_count: int
    missing_basic_nutrients: list[str]
    derived_nutrients: list[str]
    estimated_measure_count: int
    quality_level: Literal["incomplete", "basic_complete", "extended"]
    warnings: list[str]


class FoodResponse(BaseModel):
    id: UUID
    name: str
    brand: str | None
    description: str | None
    category_code: str | None
    food_type: str
    source_type: str
    source_name: str | None
    reference_quantity: Decimal
    reference_unit: str
    density_g_per_ml: Decimal | None
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    nutrients: list[NutrientResponse]
    measures: list[MeasureResponse]
    quality: QualityResponse


class FoodListResponse(BaseModel):
    items: list[FoodResponse]
    page: int
    page_size: int
    total: int


class DuplicateResponse(BaseModel):
    items: list[FoodResponse]


class ArchiveResponse(BaseModel):
    id: UUID
    archived: bool
    message_de: str


class PermanentDeleteResponse(BaseModel):
    id: UUID
    deleted: bool
    message_de: str


class BarcodePreviewResponse(BaseModel):
    barcode: str
    name: str
    brand: str | None
    quantity_label: str | None
    reference_unit: Literal["g", "ml"]
    nutrients: list[NutrientInput]
    image_url: str | None
    source_name: str
    source_version: str | None
    warnings: list[str]


class BarcodeImportRequest(BaseModel):
    preview: BarcodePreviewResponse
    confirm_incomplete: bool = False
    confirm_duplicate: bool = False
