"""Public Nutrition Engine API."""

from .assessment import NutritionEngine, build_default_engine, calculate_assessment
from .input_models import (
    ActivityCategory,
    AssessmentInput,
    DietaryPreference,
    GoalIntensity,
    GoalType,
    HealthScreening,
    Measurement,
    MeasurementSource,
    NutritionGoal,
    PhysiologicalCategory,
    SportActivity,
    SportIntensity,
    SportType,
)
from .result_models import (
    AssessmentResult,
    ConfidenceType,
    EngineInputError,
    MetricResult,
    SafetyFlag,
    SafetySeverity,
    SupportedScopeStatus,
)

__all__ = [
    "ActivityCategory",
    "AssessmentInput",
    "AssessmentResult",
    "ConfidenceType",
    "DietaryPreference",
    "EngineInputError",
    "GoalIntensity",
    "GoalType",
    "HealthScreening",
    "Measurement",
    "MeasurementSource",
    "MetricResult",
    "NutritionEngine",
    "NutritionGoal",
    "PhysiologicalCategory",
    "SafetyFlag",
    "SafetySeverity",
    "SportActivity",
    "SportIntensity",
    "SportType",
    "SupportedScopeStatus",
    "build_default_engine",
    "calculate_assessment",
]
