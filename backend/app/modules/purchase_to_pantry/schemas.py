from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.profiles.schemas import LocalizedDecimal


class DestinationInput(BaseModel):
    destination_type: Literal["new_stock_lot", "existing_stock_lot"] = "new_stock_lot"
    pantry_location_id: UUID
    target_stock_lot_id: UUID | None = None
    expected_lot_version: int | None = Field(None, ge=1)
    quantity: LocalizedDecimal = Field(gt=0, le=1_000_000_000)
    unit_code: str = Field(min_length=1, max_length=32)
    food_measure_id: UUID | None = None
    purchase_date: date | None = None
    opened_date: date | None = None
    best_before_date: date | None = None
    use_by_date: date | None = None
    note: str | None = Field(None, max_length=1000)
    confirm_same_lot_metadata: bool = False

    @model_validator(mode="after")
    def target_shape(self) -> DestinationInput:
        if self.destination_type == "existing_stock_lot" and self.target_stock_lot_id is None:
            raise ValueError("Für bestehenden Bestand fehlt die Bestands-ID.")
        if self.destination_type == "new_stock_lot" and self.target_stock_lot_id is not None:
            raise ValueError("Ein neuer Bestand darf keine Ziel-Bestands-ID enthalten.")
        return self


class HandoffItemInput(BaseModel):
    shopping_list_item_id: UUID
    mapped_food_id: UUID | None = None
    actual_quantity: LocalizedDecimal = Field(gt=0, le=1_000_000_000)
    unit_code: str = Field(min_length=1, max_length=32)
    food_measure_id: UUID | None = None
    mark_item_handoff_completed: bool = True
    confirm_additional_after_completion: bool = False
    destinations: list[DestinationInput] = Field(min_length=1)


class PreviewRequest(BaseModel):
    items: list[HandoffItemInput] = Field(min_length=1)


class ApplyRequest(PreviewRequest):
    client_operation_id: UUID
    preview_token: str = Field(min_length=16, max_length=128)
