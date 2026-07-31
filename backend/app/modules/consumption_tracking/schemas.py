from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.daily_meal_planning.enums import MealType

from .enums import Completeness, EntryType, OriginType, OutcomeType, TargetBasisSource


class DayCreate(BaseModel):
    consumption_date: date
    target_basis_source: TargetBasisSource = TargetBasisSource.LATEST
    assessment_id: UUID | None = None
    note: str | None = Field(default=None, max_length=4000)


class FromPlan(BaseModel):
    daily_plan_id: UUID
    note: str | None = Field(default=None, max_length=4000)


class DayPatch(BaseModel):
    note: str | None = Field(default=None, max_length=4000)
    expected_version: int = Field(ge=1)
    target_basis_source: TargetBasisSource | None = None
    assessment_id: UUID | None = None
    confirm_target_basis_change: bool = False


class MealWrite(BaseModel):
    meal_type: MealType
    custom_name: str | None = Field(default=None, max_length=200)
    consumed_time: time | None = None
    position: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=4000)


class EntryWrite(BaseModel):
    meal_id: UUID
    entry_type: EntryType
    origin_type: OriginType = OriginType.UNPLANNED
    food_id: UUID | None = None
    recipe_id: UUID | None = None
    manual_name: str | None = Field(default=None, max_length=200)
    entered_quantity: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    entered_unit_code: str | None = Field(default=None, max_length=32)
    entered_unit_label: str | None = Field(default=None, max_length=80)
    food_measure_id: UUID | None = None
    recipe_portion_count: Decimal | None = Field(default=None, gt=0, le=100)
    note: str | None = Field(default=None, max_length=4000)
    client_operation_id: UUID
    expected_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def shape(self) -> EntryWrite:
        if self.entry_type == EntryType.FOOD:
            if self.food_id is None or self.entered_quantity is None:
                raise ValueError("food and quantity required")
            if self.entered_unit_code is None and self.food_measure_id is None:
                raise ValueError("unit or measure required")
        elif self.entry_type == EntryType.RECIPE:
            if self.recipe_id is None or self.recipe_portion_count is None:
                raise ValueError("recipe and portions required")
        elif not (self.manual_name or "").strip():
            raise ValueError("manual name required")
        return self


class OutcomeWrite(BaseModel):
    outcome_type: OutcomeType
    meal_id: UUID | None = None
    actual_entries: list[EntryWrite] = Field(default_factory=list, max_length=20)
    note: str | None = Field(default=None, max_length=4000)
    client_operation_id: UUID
    expected_day_version: int = Field(ge=1)


class FinalizeWrite(BaseModel):
    completeness_attestation: Completeness
    confirm_warnings: bool = False
    client_operation_id: UUID
    expected_version: int = Field(ge=1)


class ReorderMeals(BaseModel):
    meal_ids: list[UUID] = Field(min_length=1, max_length=30)
    expected_version: int = Field(ge=1)


class ConfirmWholeMeal(BaseModel):
    client_operation_id: UUID
    expected_day_version: int = Field(ge=1)


class LinkDailyPlan(BaseModel):
    daily_plan_id: UUID
    confirm_conflicts: bool = False
    expected_version: int = Field(ge=1)
