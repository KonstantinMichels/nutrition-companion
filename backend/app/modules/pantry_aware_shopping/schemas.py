from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.profiles.schemas import LocalizedDecimal

SourceType = Literal["recipe", "daily_plan", "weekly_plan", "shopping_list_reconciliation"]
DateMode = Literal["include_all", "exclude_past_use_by", "exclude_all_past_dates"]


class PreviewRequest(BaseModel):
    source_type: SourceType
    recipe_id: UUID | None = None
    recipe_portion_count: LocalizedDecimal = Field(default=Decimal("1"), gt=0, le=1000)
    daily_plan_id: UUID | None = None
    week_anchor_date: date | None = None
    source_occurrence_id: UUID | None = None
    target_shopping_list_id: UUID | None = None
    create_new_list: bool = False
    new_list_name: str | None = Field(None, min_length=1, max_length=200)
    pantry_date_mode: DateMode = "include_all"
    include_other_open_lists: bool = True
    include_optional_recipe_ingredients: bool = False
    intentional_duplicate_source_ids: list[str] = Field(default_factory=list)
    excluded_food_ids: list[UUID] = Field(default_factory=list)
    target_item_resolutions: dict[str, UUID | Literal["create_separate"]] = Field(
        default_factory=dict
    )
    reset_override_item_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self) -> PreviewRequest:
        required = {
            "recipe": self.recipe_id,
            "daily_plan": self.daily_plan_id,
            "weekly_plan": self.week_anchor_date,
            "shopping_list_reconciliation": self.target_shopping_list_id,
        }[self.source_type]
        if required is None:
            raise ValueError("Die gewählte Quelle ist unvollständig.")
        if self.source_type == "recipe" and self.source_occurrence_id is None:
            raise ValueError("Für ein Rezept ist eine Vorgangs-ID erforderlich.")
        if self.create_new_list == (self.target_shopping_list_id is not None):
            raise ValueError("Wähle genau eine bestehende oder eine neue Einkaufsliste.")
        if self.create_new_list and not self.new_list_name:
            raise ValueError("Für die neue Einkaufsliste ist ein Name erforderlich.")
        return self


class ApplyRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str = Field(min_length=32, max_length=128)
    preview: PreviewRequest
