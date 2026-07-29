"""Import all ORM models so Alembic sees one complete metadata graph."""

from app.modules.foods.models import Food, FoodMeasure, FoodNutrient
from app.modules.nutrition_assessment.models import Assessment, AssessmentMetric, SafetyFlag
from app.modules.privacy.models import (
    ConsentRecord,
    DeletionRecord,
    PrivacyAction,
    ProcessingPurpose,
)
from app.modules.profiles.models import (
    ActivityProfile,
    DietaryRestriction,
    HealthScreening,
    Measurement,
    NutritionGoal,
    Profile,
    SportActivity,
)
from app.modules.recipes.models import Recipe, RecipeIngredient, RecipeStep
from app.modules.reference_data.models import ApplicationRuleSet, ReferenceSet, ReferenceValue

__all__ = [
    "ActivityProfile",
    "ApplicationRuleSet",
    "Assessment",
    "AssessmentMetric",
    "ConsentRecord",
    "DeletionRecord",
    "DietaryRestriction",
    "Food",
    "FoodMeasure",
    "FoodNutrient",
    "HealthScreening",
    "Measurement",
    "NutritionGoal",
    "PrivacyAction",
    "ProcessingPurpose",
    "Profile",
    "Recipe",
    "RecipeIngredient",
    "RecipeStep",
    "ReferenceSet",
    "ReferenceValue",
    "SafetyFlag",
    "SportActivity",
]
