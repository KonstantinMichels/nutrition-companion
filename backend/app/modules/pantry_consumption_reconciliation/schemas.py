from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

SourceContext = Literal[
    "from_pantry",
    "partially_from_pantry",
    "not_from_pantry",
    "already_accounted_for",
    "unknown",
    "prepared_from_pantry_for_this_entry",
    "leftovers_already_accounted_for",
    "not_used",
    "unresolved",
]


class LotAllocationWrite(BaseModel):
    stock_lot_id: UUID
    quantity: Decimal = Field(gt=0)
    expected_lot_version: int = Field(ge=1)


class RequirementDecision(BaseModel):
    recipe_ingredient_snapshot_id: UUID | None = None
    food_id: UUID | None = None
    food_name_snapshot: str | None = Field(None, max_length=200)
    source_context: SourceContext = "unknown"
    selected_pantry_quantity: Decimal = Field(default=Decimal(0), ge=0)
    allocations: list[LotAllocationWrite] = Field(default_factory=list)
    include_optional: bool = False


class EntryDecision(BaseModel):
    consumption_entry_id: UUID
    expected_entry_version: int = Field(ge=1)
    source_context: SourceContext = "unknown"
    selected_pantry_quantity: Decimal | None = Field(None, ge=0)
    allocations: list[LotAllocationWrite] = Field(default_factory=list)
    requirements: list[RequirementDecision] = Field(default_factory=list)


class PreviewRequest(BaseModel):
    expected_day_version: int = Field(ge=1)
    entries: list[EntryDecision]
    apply_mode: Literal["all_or_nothing", "apply_selected_valid_items"] = "all_or_nothing"
    confirm_legacy_recipe_snapshot: bool = False


class ApplyRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str = Field(min_length=16)
    preview: PreviewRequest
    past_use_by_confirmations: list[UUID] = Field(default_factory=list)


class ReversalSelection(BaseModel):
    allocation_id: UUID
    quantity: Decimal = Field(gt=0)
    target_lot_id: UUID | None = None


class ReversalPreviewRequest(BaseModel):
    selections: list[ReversalSelection]
    reason: Literal[
        "wrong_consumption_entry",
        "wrong_quantity",
        "wrong_lot",
        "duplicate_deduction",
        "consumption_entry_deleted",
        "other",
    ]
    note: str | None = Field(None, max_length=1000)


class ReversalApplyRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str = Field(min_length=16)
    preview: ReversalPreviewRequest


class EntryDeletionResolution(BaseModel):
    policy: Literal["reverse_and_delete", "keep_pantry_movements_and_delete", "cancel"]
    client_operation_id: UUID | None = None

    @model_validator(mode="after")
    def operation_required(self) -> Self:
        if self.policy == "reverse_and_delete" and self.client_operation_id is None:
            raise ValueError("Für die Gegenbewegung ist eine Vorgangs-ID erforderlich.")
        return self


class DayDeletionResolution(BaseModel):
    policy: Literal["reverse_all_and_delete", "keep_all_movements_and_delete", "cancel"]
    client_operation_id: UUID | None = None
