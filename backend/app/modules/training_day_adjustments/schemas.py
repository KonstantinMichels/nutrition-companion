from __future__ import annotations

from datetime import date as Date
from datetime import time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .enums import BaselineInclusion, Intensity, SessionType, SportType, Strategy


class SessionWrite(BaseModel):
    session_date: Date
    planned_start_time: time | None = None
    sport_type: SportType
    session_type: SessionType
    planned_duration_minutes: int = Field(ge=5, le=720)
    perceived_intensity: Intensity
    baseline_inclusion: BaselineInclusion = BaselineInclusion.UNKNOWN
    title: str | None = Field(None, max_length=200)
    note: str | None = Field(None, max_length=4000)
    expected_version: int | None = None
    confirm_long_duration: bool = False


class PreferenceWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    is_default: bool = False
    default_baseline_assessment_mode: Literal[
        "latest_usable", "explicit", "daily_plan_assessment"
    ] = "latest_usable"
    explicit_assessment_id: UUID | None = None
    default_strategy: Strategy = Strategy.NONE
    positive_energy_cap_kcal: Decimal = Field(Decimal("300"), ge=0, le=1000)
    negative_energy_cap_kcal: Decimal = Field(Decimal("250"), ge=0, le=1000)
    relative_energy_cap: Decimal = Field(Decimal("0.15"), ge=0, le=Decimal("0.25"))
    carbohydrate_adjustments_enabled: bool = True
    redistribution_enabled: bool = True
    minimum_rest_day_target_kcal: Decimal | None = Field(None, ge=0)
    include_cancelled_sessions: bool = False

    @model_validator(mode="after")
    def assessment(self) -> PreferenceWrite:
        if (
            self.default_baseline_assessment_mode == "explicit"
            and self.explicit_assessment_id is None
        ):
            raise ValueError("Für den expliziten Modus ist ein Assessment erforderlich.")
        return self


class PreviewRequest(BaseModel):
    scope: Literal["single_day", "iso_week"]
    date: Date | None = None
    week_anchor_date: Date | None = None
    source_assessment_id: UUID | None = None
    preference_id: UUID | None = None
    strategy: Strategy
    session_ids: list[UUID] | None = None
    redistribution_strength: Decimal = Field(Decimal("1"), ge=0, le=1)
    selected_energy_deltas: dict[str, Decimal] = Field(default_factory=dict)
    selected_carbohydrate_deltas: dict[str, Decimal] = Field(default_factory=dict)

    @model_validator(mode="after")
    def scope_date(self) -> PreviewRequest:
        if self.scope == "single_day" and self.date is None:
            raise ValueError("Für einen Tag ist ein Datum erforderlich.")
        if self.scope == "iso_week" and self.week_anchor_date is None:
            raise ValueError("Für eine Woche ist ein Ankerdatum erforderlich.")
        return self


class ApplyRequest(BaseModel):
    preview_token: str = Field(min_length=16)
    client_operation_id: UUID
    preview: PreviewRequest
    replacement_confirmation_ids: list[UUID] = Field(default_factory=list)
    link_to_daily_plan_dates: list[Date] = Field(default_factory=list)
    create_missing_plan_dates: list[Date] = Field(default_factory=list)


class PlanLinkRequest(BaseModel):
    daily_plan_id: UUID | None = None
    create_missing_plan: bool = False
