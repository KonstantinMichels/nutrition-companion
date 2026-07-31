from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PreviewRequest(BaseModel):
    method: Literal["target_response_proxy", "intake_informed"] = "target_response_proxy"
    source_assessment_id: UUID | None = None
    window_start: date
    window_end: date
    adherence: Literal["high", "moderate", "low", "unknown"] = "unknown"
    context_stability: Literal["stable", "minor_changes", "major_changes", "unknown"] = "unknown"
    recording_confidence: Literal["high", "moderate", "low", "unknown"] = "unknown"
    routine_representativeness: Literal[
        "representative", "minor_changes", "major_changes", "unknown"
    ] = "unknown"
    included_consumption_day_ids: list[UUID] = Field(default_factory=list)
    excluded_consumption_day_ids: list[UUID] = Field(default_factory=list)
    included_weight_observation_ids: list[UUID] = Field(default_factory=list)
    excluded_weight_observation_ids: list[UUID] = Field(default_factory=list)
    conditional_day_confirmations: list[UUID] = Field(default_factory=list)
    consumption_exclusion_reasons: dict[
        UUID,
        Literal[
            "unrepresentative_day",
            "possible_quantity_error",
            "special_event",
            "temporary_condition",
            "other",
        ],
    ] = Field(default_factory=dict)
    weight_exclusion_reasons: dict[UUID, str] = Field(default_factory=dict)


class ApplyRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str = Field(min_length=16)
    preview: PreviewRequest
    accepted_adjustment_kcal_per_day: Decimal | None = None


class DeclineRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str = Field(min_length=16)
    preview: PreviewRequest
