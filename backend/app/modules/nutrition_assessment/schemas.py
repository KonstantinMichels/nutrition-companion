from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentCreateRequest(BaseModel):
    client_request_id: UUID


class MetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_code: str
    raw_value: Decimal | None
    display_value: str
    lower_value: Decimal | None
    upper_value: Decimal | None
    unit: str
    method_code: str
    explanation_de: str
    limitations_de: str
    calculation_inputs: dict[str, Any]
    source_metadata: dict[str, Any]
    application_rule_identifier: str | None
    confidence_type: str


class SafetyFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    severity: str
    explanation_de: str
    recommended_action_de: str


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supported_scope_status: str
    reference_set_identifier: str
    reference_set_version: str
    application_rule_set_identifier: str
    application_rule_set_version: str
    engine_version: str
    calculated_at: datetime
    summary: dict[str, Any]
    metrics: list[MetricResponse]
    safety_flags: list[SafetyFlagResponse]


class AssessmentHistoryItem(BaseModel):
    id: UUID
    calculated_at: datetime
    supported_scope_status: str
    goal_type: str
    energy_target_summary: str | None
    warning_codes: list[str]


class AssessmentHistoryResponse(BaseModel):
    items: list[AssessmentHistoryItem]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
