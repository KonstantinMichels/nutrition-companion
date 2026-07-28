from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator


def _normalize_decimal(value: object) -> object:
    if isinstance(value, str):
        cleaned = value.strip()
        if "," in cleaned and "." in cleaned:
            raise ValueError("mixed decimal separators")
        return cleaned.replace(",", ".")
    return value


LocalizedDecimal = Annotated[Decimal, BeforeValidator(_normalize_decimal)]
PhysiologicalCategory = Literal["reference_category_a", "reference_category_b"]
DietaryPreference = Literal["mixed", "vegetarian", "vegan", "other"]
MeasurementType = Literal[
    "weight",
    "body_fat_percentage",
    "waist_circumference",
    "hip_circumference",
    "measured_resting_energy_expenditure",
]
MeasurementSource = Literal["measured", "device_estimate", "user_estimate"]
ActivityCategory = Literal[
    "mostly_seated",
    "seated_with_walking",
    "mostly_standing_walking",
    "physically_demanding",
]
SportType = Literal[
    "strength_training",
    "cycling",
    "running",
    "swimming",
    "endurance_training",
    "team_sport",
    "mixed_training",
    "mobility_recovery",
    "other",
]
Intensity = Literal["light", "moderate", "vigorous"]
GoalType = Literal[
    "maintain_weight",
    "lose_weight",
    "gain_weight",
    "general_health",
    "athletic_performance",
]


class MeasurementInput(BaseModel):
    measurement_type: MeasurementType
    value: LocalizedDecimal
    unit: str = Field(min_length=1, max_length=24)
    measured_at: date
    source_type: MeasurementSource

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Decimal, info: object) -> Decimal:
        if not value.is_finite():
            raise ValueError("finite value required")
        return value

    @field_validator("measured_at")
    @classmethod
    def validate_measurement_date(cls, value: date) -> date:
        if value > date.today() + timedelta(days=1):
            raise ValueError("measurement date too far in the future")
        if value < date.today() - timedelta(days=365 * 120):
            raise ValueError("measurement date is implausibly old")
        return value

    @model_validator(mode="after")
    def validate_type_specific_value(self) -> MeasurementInput:
        allowed = {
            "weight": (Decimal("25"), Decimal("350"), "kg"),
            "body_fat_percentage": (Decimal("2"), Decimal("75"), "%"),
            "waist_circumference": (Decimal("30"), Decimal("250"), "cm"),
            "hip_circumference": (Decimal("30"), Decimal("250"), "cm"),
            "measured_resting_energy_expenditure": (Decimal("500"), Decimal("5000"), "kcal/day"),
        }
        lower, upper, expected_unit = allowed[self.measurement_type]
        if not lower <= self.value <= upper:
            raise ValueError("measurement outside plausible range")
        if self.unit != expected_unit:
            raise ValueError(f"expected unit {expected_unit}")
        return self


class MeasurementResponse(MeasurementInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class ProfileUpdate(BaseModel):
    birth_date: date
    physiological_category: PhysiologicalCategory
    height_cm: LocalizedDecimal = Field(gt=Decimal("100"), le=Decimal("250"))
    current_weight_kg: LocalizedDecimal = Field(gt=Decimal("25"), le=Decimal("350"))
    dietary_preference: DietaryPreference
    preferred_meals_per_day: int | None = Field(default=None, ge=1, le=12)
    preferred_meal_timing: str | None = Field(default=None, max_length=200)
    measurements: Sequence[MeasurementInput] = Field(default_factory=list, max_length=10)

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date) -> date:
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 13 or age > 120:
            raise ValueError("age outside plausible range")
        return value

    @field_validator("height_cm", "current_weight_kg")
    @classmethod
    def validate_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("finite value required")
        return value

    @model_validator(mode="after")
    def unique_measurement_types(self) -> ProfileUpdate:
        types = [item.measurement_type for item in self.measurements]
        if len(types) != len(set(types)):
            raise ValueError("only one current measurement per type is accepted")
        return self


class ProfileResponse(ProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    measurements: Sequence[MeasurementResponse]


class SportActivityInput(BaseModel):
    sport_type: SportType
    sessions_per_week: LocalizedDecimal = Field(ge=Decimal("0"), le=Decimal("14"))
    minutes_per_session: int = Field(ge=0, le=600)
    intensity: Intensity
    note: str | None = Field(default=None, max_length=500)

    @field_validator("sessions_per_week")
    @classmethod
    def finite_sessions(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("finite value required")
        return value


class SportActivityResponse(SportActivityInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ActivityUpdate(BaseModel):
    occupational_activity_category: ActivityCategory
    average_daily_steps: int | None = Field(default=None, ge=0, le=100_000)
    active_commuting: bool = False
    movement_notes: str | None = Field(default=None, max_length=500)
    manual_pal_override: LocalizedDecimal | None = Field(
        default=None, ge=Decimal("1.2"), le=Decimal("2.4")
    )
    sports: Sequence[SportActivityInput] = Field(default_factory=list, max_length=30)

    @field_validator("manual_pal_override")
    @classmethod
    def finite_pal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("finite value required")
        return value


class ActivityResponse(ActivityUpdate):
    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID
    created_at: datetime
    updated_at: datetime
    sports: Sequence[SportActivityResponse]


class GoalUpdate(BaseModel):
    goal_type: GoalType
    target_weight_kg: LocalizedDecimal | None = Field(
        default=None, gt=Decimal("25"), le=Decimal("350")
    )
    desired_intensity: Literal["mild", "moderate"] | None = None
    requested_weekly_rate_kg: LocalizedDecimal | None = Field(
        default=None, gt=Decimal("0"), le=Decimal("2")
    )

    @field_validator("target_weight_kg", "requested_weekly_rate_kg")
    @classmethod
    def finite_optional(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("finite value required")
        return value

    @model_validator(mode="after")
    def validate_goal_options(self) -> GoalUpdate:
        if self.goal_type in {"lose_weight", "gain_weight"} and self.desired_intensity is None:
            raise ValueError("desired_intensity is required for weight change goals")
        if self.goal_type not in {"lose_weight", "gain_weight"} and (
            self.desired_intensity is not None or self.requested_weekly_rate_kg is not None
        ):
            raise ValueError("weight change options require a weight change goal")
        return self


class GoalResponse(GoalUpdate):
    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID
    created_at: datetime
    updated_at: datetime


class RestrictionInput(BaseModel):
    restriction_type: Literal["allergy", "intolerance", "excluded_food", "disliked_food"]
    value: str = Field(min_length=1, max_length=200)
    hard_exclusion: bool = False
    note: str | None = Field(default=None, max_length=500)

    @field_validator("value")
    @classmethod
    def non_blank_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("blank restriction")
        return value


class RestrictionResponse(RestrictionInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID


class RestrictionsUpdate(BaseModel):
    restrictions: list[RestrictionInput] = Field(default_factory=list, max_length=100)


class RestrictionsResponse(BaseModel):
    restrictions: list[RestrictionResponse]


class HealthScreeningUpdate(BaseModel):
    pregnant: bool = False
    breastfeeding: bool = False
    diagnosed_eating_disorder: bool = False
    diabetes: bool = False
    kidney_disease: bool = False
    liver_disease: bool = False
    medically_prescribed_diet: bool = False
    serious_metabolic_condition: bool = False
    other_professional_nutrition_condition: bool = False
    user_note: str | None = Field(default=None, max_length=1000)


class HealthScreeningResponse(HealthScreeningUpdate):
    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID
    screened_at: datetime
