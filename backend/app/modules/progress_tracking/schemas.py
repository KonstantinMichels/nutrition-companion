from datetime import date, time
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

WeightUnit = Literal["kg", "lb"]
Context = Literal[
    "morning", "evening", "before_meal", "after_meal", "after_training", "other", "unspecified"
]
MeasurementType = Literal[
    "waist",
    "hip",
    "neck",
    "chest",
    "upper_arm_left",
    "upper_arm_right",
    "thigh_left",
    "thigh_right",
    "calf_left",
    "calf_right",
    "other",
]
CompositionMethod = Literal[
    "bioelectrical_impedance",
    "caliper",
    "dexa",
    "hydrostatic",
    "manual_estimate",
    "other",
    "unspecified",
]


class WeightWrite(BaseModel):
    observed_on: date
    observed_time: time | None = None
    entered_weight: Decimal = Field(gt=0)
    entered_unit: WeightUnit
    measurement_context: Context = "unspecified"
    note: str | None = Field(default=None, max_length=2000)
    confirm_unusual_change: bool = False
    expected_version: int | None = Field(default=None, ge=1)


class MeasurementWrite(BaseModel):
    measurement_type: MeasurementType
    observed_on: date
    observed_time: time | None = None
    entered_value: Decimal = Field(gt=0)
    entered_unit: Literal["cm", "in"]
    measurement_method: Literal["tape_measure", "device", "estimated", "other", "unspecified"] = (
        "tape_measure"
    )
    note: str | None = Field(default=None, max_length=2000)
    expected_version: int | None = Field(default=None, ge=1)


class CompositionWrite(BaseModel):
    observed_on: date
    observed_time: time | None = None
    body_fat_percent: Decimal | None = None
    lean_mass_kg: Decimal | None = None
    fat_mass_kg: Decimal | None = None
    measurement_method: CompositionMethod = "unspecified"
    device_name: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    expected_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def any_value(self) -> Self:
        if all(v is None for v in (self.body_fat_percent, self.lean_mass_kg, self.fat_mass_kg)):
            raise ValueError("Mindestens ein Körperzusammensetzungswert ist erforderlich.")
        return self


class GoalWrite(BaseModel):
    goal_type: Literal["lose_weight", "gain_weight", "maintain_weight", "custom"]
    start_date: date
    start_weight_kg: Decimal | None = None
    use_latest_weight: bool = False
    target_weight_kg: Decimal | None = None
    target_weight_min_kg: Decimal | None = None
    target_weight_max_kg: Decimal | None = None
    target_date: date | None = None
    note: str | None = Field(default=None, max_length=2000)
    replace_active: bool = False
    expected_version: int | None = Field(default=None, ge=1)
