from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.profiles.schemas import LocalizedDecimal


class ListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = None


class ListPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    notes: str | None = None
    pantry_considered: bool | None = None


class GenerationRequest(BaseModel):
    daily_plan_id: UUID | None = None
    week_anchor_date: date | None = None
    pantry_considered: bool = True
    name: str | None = Field(None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def exactly_one_source(self) -> GenerationRequest:
        if (self.daily_plan_id is None) == (self.week_anchor_date is None):
            raise ValueError("Genau eine Planquelle muss ausgewählt werden.")
        return self


class ItemCreate(BaseModel):
    food_id: UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    quantity: LocalizedDecimal | None = Field(None, gt=0)
    unit_code: str | None = Field(None, max_length=32)
    food_measure_id: UUID | None = None
    category_code: str = Field("other", max_length=48)
    note: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def valid_item(self) -> ItemCreate:
        if (self.food_id is None) == (self.name is None):
            raise ValueError("Lebensmittel oder Freitext muss angegeben werden.")
        if self.food_id is not None and (self.quantity is None or self.unit_code is None):
            raise ValueError("Für ein Lebensmittel sind Menge und Einheit erforderlich.")
        return self


class ItemPatch(BaseModel):
    purchase_quantity: LocalizedDecimal | None = Field(None, gt=0)
    purchase_unit_code: str | None = Field(None, max_length=32)
    category_code: str | None = Field(None, max_length=48)
    note: str | None = Field(None, max_length=1000)
    manual_name: str | None = Field(None, min_length=1, max_length=200)
    manual_quantity: LocalizedDecimal | None = Field(None, gt=0)
    manual_unit_label: str | None = Field(None, max_length=32)
    is_checked: bool | None = None
    reset_to_suggestion: bool = False


class ReorderRequest(BaseModel):
    item_ids: list[UUID] = Field(min_length=1)


class RefreshRequest(BaseModel):
    preview_version: int = Field(ge=1)


SourceType = Literal["daily_plan", "weekly_plan"]
