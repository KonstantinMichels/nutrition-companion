from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PreviewRequest(BaseModel):
    source_assessment_id: UUID | None = None
    window_start: date
    window_end: date
    adherence: Literal["high", "moderate", "low", "unknown"]
    context_stability: Literal["stable", "minor_changes", "major_changes", "unknown"]


class ApplyRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str = Field(min_length=16)
    preview: PreviewRequest
    accepted_adjustment_kcal_per_day: Decimal | None = None


class DeclineRequest(BaseModel):
    client_operation_id: UUID
    preview_token: str = Field(min_length=16)
    preview: PreviewRequest
