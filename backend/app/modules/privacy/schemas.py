from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProcessingPurposeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    description_de: str
    data_categories: list[str]
    may_include_special_category_data: bool
    storage_location: str
    retention_period: str
    legal_basis_placeholder: str
    consent_required: bool
    recipients_or_processors: list[str]
    deletion_behavior_de: str
    required: bool
    registry_version: str


class ConsentCreate(BaseModel):
    purpose_code: Literal["nutrition_assessment_calculation"]
    consent_text_version: str = Field(min_length=1, max_length=100)
    affirmed: bool
    source: Literal["android_onboarding", "android_privacy_settings"] = "android_onboarding"


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purpose_code: str
    consent_text_version: str
    status: str
    granted_at: datetime
    withdrawn_at: datetime | None
    source: str
    created_at: datetime


class PrivacyExportResponse(BaseModel):
    export_format: Literal["nutrition_companion_json_v1"] = "nutrition_companion_json_v1"
    generated_at: datetime
    notice_de: str
    data: dict[str, Any]


class DeletionResponse(BaseModel):
    deleted: bool
    scope: Literal["assessment_history", "complete_profile"]
    confirmation_code: str
    message_de: str


class DeletionConfirmation(BaseModel):
    confirm: Literal[True]
