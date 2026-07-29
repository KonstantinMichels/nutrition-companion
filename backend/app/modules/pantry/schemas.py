from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

LocationType = Literal["pantry", "refrigerator", "freezer", "kitchen", "cellar", "other"]


class LocationWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location_type: LocationType
    position: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class LocationPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location_type: LocationType | None = None
    position: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=4000)


class StockCreate(BaseModel):
    client_operation_id: UUID
    food_id: UUID
    location_id: UUID
    quantity: Decimal = Field(gt=0, le=1_000_000_000)
    unit_code: str = Field(min_length=1, max_length=32)
    food_measure_id: UUID | None = None
    purchase_date: date | None = None
    opened_date: date | None = None
    best_before_date: date | None = None
    use_by_date: date | None = None
    note: str | None = Field(default=None, max_length=1000)


class StockPatch(BaseModel):
    purchase_date: date | None = None
    opened_date: date | None = None
    best_before_date: date | None = None
    use_by_date: date | None = None
    note: str | None = Field(default=None, max_length=1000)


class QuantityOperation(BaseModel):
    client_operation_id: UUID
    quantity: Decimal = Field(gt=0, le=1_000_000_000)
    unit_code: str = Field(min_length=1, max_length=32)
    food_measure_id: UUID | None = None
    note: str | None = Field(default=None, max_length=1000)
    confirm_depleted_reuse: bool = False


class CorrectionOperation(BaseModel):
    client_operation_id: UUID
    new_total_quantity: Decimal = Field(ge=0, le=1_000_000_000)
    unit_code: str = Field(min_length=1, max_length=32)
    food_measure_id: UUID | None = None
    note: str | None = Field(default=None, max_length=1000)


class TransferOperation(QuantityOperation):
    target_location_id: UUID


class ArchiveRequest(BaseModel):
    confirm_non_depleted: bool = False
