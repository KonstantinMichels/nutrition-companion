"""Typed, immutable inputs for the pure Nutrition Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from .numeric import DecimalLike, as_decimal


class PhysiologicalCategory(StrEnum):
    """Equation/reference-table category; it is not a gender identity field."""

    REFERENCE_CATEGORY_A = "reference_category_a"
    REFERENCE_CATEGORY_B = "reference_category_b"


class ActivityCategory(StrEnum):
    MOSTLY_SEATED = "mostly_seated"
    SEATED_WITH_WALKING = "seated_with_walking"
    MOSTLY_STANDING_WALKING = "mostly_standing_walking"
    PHYSICALLY_DEMANDING = "physically_demanding"


class SportType(StrEnum):
    STRENGTH_TRAINING = "strength_training"
    CYCLING = "cycling"
    RUNNING = "running"
    SWIMMING = "swimming"
    ENDURANCE_TRAINING = "endurance_training"
    TEAM_SPORT = "team_sport"
    MIXED_TRAINING = "mixed_training"
    MOBILITY_RECOVERY = "mobility_recovery"
    OTHER = "other"


class SportIntensity(StrEnum):
    LIGHT = "light"
    MODERATE = "moderate"
    VIGOROUS = "vigorous"


class GoalType(StrEnum):
    MAINTAIN_WEIGHT = "maintain_weight"
    LOSE_WEIGHT = "lose_weight"
    GAIN_WEIGHT = "gain_weight"
    GENERAL_HEALTH = "general_health"
    ATHLETIC_PERFORMANCE = "athletic_performance"


class GoalIntensity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"


class MeasurementSource(StrEnum):
    MEASURED = "measured"
    DEVICE_ESTIMATE = "device_estimate"
    USER_ESTIMATE = "user_estimate"


class DietaryPreference(StrEnum):
    MIXED = "mixed"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Measurement:
    value: Decimal
    unit: str
    measured_at: date
    source_type: MeasurementSource

    def __init__(
        self,
        value: DecimalLike,
        unit: str,
        measured_at: date,
        source_type: MeasurementSource | str,
    ) -> None:
        object.__setattr__(self, "value", as_decimal(value, field="measurement.value"))
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "measured_at", measured_at)
        object.__setattr__(self, "source_type", MeasurementSource(source_type))


@dataclass(frozen=True, slots=True)
class SportActivity:
    sport_type: SportType
    sessions_per_week: Decimal
    minutes_per_session: Decimal
    intensity: SportIntensity
    note: str | None = None

    def __init__(
        self,
        sport_type: SportType | str,
        sessions_per_week: DecimalLike,
        minutes_per_session: DecimalLike,
        intensity: SportIntensity | str,
        note: str | None = None,
    ) -> None:
        sessions = as_decimal(sessions_per_week, field="sessions_per_week")
        minutes = as_decimal(minutes_per_session, field="minutes_per_session")
        if sessions < 0 or minutes < 0:
            raise ValueError("sport duration and frequency must not be negative")
        object.__setattr__(self, "sport_type", SportType(sport_type))
        object.__setattr__(self, "sessions_per_week", sessions)
        object.__setattr__(self, "minutes_per_session", minutes)
        object.__setattr__(self, "intensity", SportIntensity(intensity))
        object.__setattr__(self, "note", note)

    @property
    def weekly_minutes(self) -> Decimal:
        return self.sessions_per_week * self.minutes_per_session


@dataclass(frozen=True, slots=True)
class NutritionGoal:
    goal_type: GoalType
    desired_intensity: GoalIntensity | None = None
    target_weight_kg: Decimal | None = None
    requested_weekly_rate_kg: Decimal | None = None

    def __init__(
        self,
        goal_type: GoalType | str,
        desired_intensity: GoalIntensity | str | None = None,
        target_weight_kg: DecimalLike | None = None,
        requested_weekly_rate_kg: DecimalLike | None = None,
    ) -> None:
        parsed_goal = GoalType(goal_type)
        parsed_intensity = GoalIntensity(desired_intensity) if desired_intensity else None
        if parsed_goal in {GoalType.LOSE_WEIGHT, GoalType.GAIN_WEIGHT}:
            if parsed_intensity is None:
                raise ValueError("weight-change goals require desired_intensity")
        elif parsed_intensity is not None or requested_weekly_rate_kg is not None:
            raise ValueError("weight-change options require a weight-change goal")
        object.__setattr__(self, "goal_type", parsed_goal)
        object.__setattr__(self, "desired_intensity", parsed_intensity)
        object.__setattr__(
            self,
            "target_weight_kg",
            None
            if target_weight_kg is None
            else as_decimal(target_weight_kg, field="target_weight_kg"),
        )
        object.__setattr__(
            self,
            "requested_weekly_rate_kg",
            None
            if requested_weekly_rate_kg is None
            else as_decimal(requested_weekly_rate_kg, field="requested_weekly_rate_kg"),
        )


@dataclass(frozen=True, slots=True)
class HealthScreening:
    pregnant: bool = False
    breastfeeding: bool = False
    diagnosed_eating_disorder: bool = False
    diabetes: bool = False
    kidney_disease: bool = False
    liver_disease: bool = False
    medically_prescribed_diet: bool = False
    serious_metabolic_condition: bool = False
    other_professional_nutrition_condition: bool = False

    def active_flags(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in (
                "pregnant",
                "breastfeeding",
                "diagnosed_eating_disorder",
                "diabetes",
                "kidney_disease",
                "liver_disease",
                "medically_prescribed_diet",
                "serious_metabolic_condition",
                "other_professional_nutrition_condition",
            )
            if getattr(self, name)
        )


@dataclass(frozen=True, slots=True)
class AssessmentInput:
    age_years: int
    height_cm: Decimal
    weight_kg: Decimal
    physiological_category: PhysiologicalCategory
    activity_category: ActivityCategory
    goal: NutritionGoal
    sports: tuple[SportActivity, ...] = field(default_factory=tuple)
    manual_pal_override: Decimal | None = None
    body_fat_percentage: Measurement | None = None
    waist_circumference: Measurement | None = None
    hip_circumference: Measurement | None = None
    measured_resting_energy_expenditure: Measurement | None = None
    health_screening: HealthScreening = field(default_factory=HealthScreening)
    dietary_preference: DietaryPreference = DietaryPreference.MIXED

    def __init__(
        self,
        *,
        age_years: int,
        height_cm: DecimalLike,
        weight_kg: DecimalLike,
        physiological_category: PhysiologicalCategory | str,
        activity_category: ActivityCategory | str,
        goal: NutritionGoal,
        sports: tuple[SportActivity, ...] | list[SportActivity] = (),
        manual_pal_override: DecimalLike | None = None,
        body_fat_percentage: Measurement | None = None,
        waist_circumference: Measurement | None = None,
        hip_circumference: Measurement | None = None,
        measured_resting_energy_expenditure: Measurement | None = None,
        health_screening: HealthScreening | None = None,
        dietary_preference: DietaryPreference | str = DietaryPreference.MIXED,
    ) -> None:
        if isinstance(age_years, bool) or not isinstance(age_years, int):
            raise TypeError("age_years must be an integer")
        object.__setattr__(self, "age_years", age_years)
        object.__setattr__(self, "height_cm", as_decimal(height_cm, field="height_cm"))
        object.__setattr__(self, "weight_kg", as_decimal(weight_kg, field="weight_kg"))
        object.__setattr__(
            self, "physiological_category", PhysiologicalCategory(physiological_category)
        )
        object.__setattr__(self, "activity_category", ActivityCategory(activity_category))
        object.__setattr__(self, "goal", goal)
        object.__setattr__(self, "sports", tuple(sports))
        object.__setattr__(
            self,
            "manual_pal_override",
            None
            if manual_pal_override is None
            else as_decimal(manual_pal_override, field="manual_pal_override"),
        )
        object.__setattr__(self, "body_fat_percentage", body_fat_percentage)
        object.__setattr__(self, "waist_circumference", waist_circumference)
        object.__setattr__(self, "hip_circumference", hip_circumference)
        object.__setattr__(
            self,
            "measured_resting_energy_expenditure",
            measured_resting_energy_expenditure,
        )
        object.__setattr__(self, "health_screening", health_screening or HealthScreening())
        object.__setattr__(self, "dietary_preference", DietaryPreference(dietary_preference))

    @property
    def total_weekly_exercise_minutes(self) -> Decimal:
        return sum((sport.weekly_minutes for sport in self.sports), Decimal(0))

    def to_snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe immutable-assessment input representation."""

        def measurement(value: Measurement | None) -> dict[str, str] | None:
            if value is None:
                return None
            return {
                "value": str(value.value),
                "unit": value.unit,
                "measured_at": value.measured_at.isoformat(),
                "source_type": value.source_type.value,
            }

        return {
            "age_years": self.age_years,
            "height_cm": str(self.height_cm),
            "weight_kg": str(self.weight_kg),
            "physiological_category": self.physiological_category.value,
            "activity_category": self.activity_category.value,
            "goal": {
                "goal_type": self.goal.goal_type.value,
                "desired_intensity": (
                    self.goal.desired_intensity.value if self.goal.desired_intensity else None
                ),
                "target_weight_kg": (
                    str(self.goal.target_weight_kg)
                    if self.goal.target_weight_kg is not None
                    else None
                ),
                "requested_weekly_rate_kg": (
                    str(self.goal.requested_weekly_rate_kg)
                    if self.goal.requested_weekly_rate_kg is not None
                    else None
                ),
            },
            "sports": [
                {
                    "sport_type": sport.sport_type.value,
                    "sessions_per_week": str(sport.sessions_per_week),
                    "minutes_per_session": str(sport.minutes_per_session),
                    "intensity": sport.intensity.value,
                    "note": sport.note,
                }
                for sport in self.sports
            ],
            "manual_pal_override": (
                str(self.manual_pal_override) if self.manual_pal_override is not None else None
            ),
            "body_fat_percentage": measurement(self.body_fat_percentage),
            "waist_circumference": measurement(self.waist_circumference),
            "hip_circumference": measurement(self.hip_circumference),
            "measured_resting_energy_expenditure": measurement(
                self.measured_resting_energy_expenditure
            ),
            "health_screening": {
                name: getattr(self.health_screening, name)
                for name in self.health_screening.__dataclass_fields__
            },
            "dietary_preference": self.dietary_preference.value,
        }
