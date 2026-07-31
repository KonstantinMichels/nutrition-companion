"""Import all ORM models so Alembic sees one complete metadata graph."""

from app.modules.consumption_tracking.models import (
    ConsumptionDay,
    ConsumptionEntry,
    ConsumptionEntryNutrientSnapshot,
    ConsumptionMeal,
    PlannedEntryConsumptionOutcome,
)
from app.modules.daily_meal_planning.models import DailyMealPlan, Meal, MealEntry
from app.modules.energy_calibration.models import (
    EnergyCalibrationConsumptionEvidence,
    EnergyCalibrationRecord,
    EnergyCalibrationWeightEvidence,
)
from app.modules.foods.models import Food, FoodMeasure, FoodNutrient
from app.modules.meal_plan_automation.models import (
    AutomationApplication,
    AutomationMealSlot,
    AutomationPreferences,
)
from app.modules.nutrition_assessment.models import Assessment, AssessmentMetric, SafetyFlag
from app.modules.pantry.models import PantryLocation, PantryMovement, PantryStockLot
from app.modules.pantry_aware_shopping.models import PantryAwareShoppingOperation
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
from app.modules.progress_tracking.models import (
    BodyCompositionObservation,
    BodyMeasurementObservation,
    BodyWeightObservation,
    ProgressGoal,
)
from app.modules.purchase_to_pantry.models import (
    PurchaseToPantryDestination,
    PurchaseToPantryHandoff,
    PurchaseToPantryHandoffItem,
)
from app.modules.recipes.models import Recipe, RecipeIngredient, RecipeStep
from app.modules.reference_data.models import ApplicationRuleSet, ReferenceSet, ReferenceValue
from app.modules.shopping_lists.models import ShoppingList, ShoppingListItem, ShoppingListItemSource
from app.modules.training_day_adjustments.models import (
    TrainingAdjustmentBatch,
    TrainingAdjustmentPreference,
    TrainingDayTargetAdjustment,
    TrainingSession,
)

__all__ = [
    "ActivityProfile",
    "ApplicationRuleSet",
    "Assessment",
    "AssessmentMetric",
    "AutomationApplication",
    "AutomationMealSlot",
    "AutomationPreferences",
    "BodyCompositionObservation",
    "BodyMeasurementObservation",
    "BodyWeightObservation",
    "ConsentRecord",
    "ConsumptionDay",
    "ConsumptionEntry",
    "ConsumptionEntryNutrientSnapshot",
    "ConsumptionMeal",
    "DailyMealPlan",
    "DeletionRecord",
    "DietaryRestriction",
    "EnergyCalibrationConsumptionEvidence",
    "EnergyCalibrationRecord",
    "EnergyCalibrationWeightEvidence",
    "Food",
    "FoodMeasure",
    "FoodNutrient",
    "HealthScreening",
    "Meal",
    "MealEntry",
    "Measurement",
    "NutritionGoal",
    "PantryAwareShoppingOperation",
    "PantryLocation",
    "PantryMovement",
    "PantryStockLot",
    "PlannedEntryConsumptionOutcome",
    "PrivacyAction",
    "ProcessingPurpose",
    "Profile",
    "ProgressGoal",
    "PurchaseToPantryDestination",
    "PurchaseToPantryHandoff",
    "PurchaseToPantryHandoffItem",
    "Recipe",
    "RecipeIngredient",
    "RecipeStep",
    "ReferenceSet",
    "ReferenceValue",
    "SafetyFlag",
    "ShoppingList",
    "ShoppingListItem",
    "ShoppingListItemSource",
    "SportActivity",
    "TrainingAdjustmentBatch",
    "TrainingAdjustmentPreference",
    "TrainingDayTargetAdjustment",
    "TrainingSession",
]
