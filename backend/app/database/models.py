"""Import all ORM models so Alembic sees one complete metadata graph."""

from app.modules.daily_meal_planning.models import DailyMealPlan, Meal, MealEntry
from app.modules.foods.models import Food, FoodMeasure, FoodNutrient
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
from app.modules.purchase_to_pantry.models import (
    PurchaseToPantryDestination,
    PurchaseToPantryHandoff,
    PurchaseToPantryHandoffItem,
)
from app.modules.recipes.models import Recipe, RecipeIngredient, RecipeStep
from app.modules.reference_data.models import ApplicationRuleSet, ReferenceSet, ReferenceValue
from app.modules.shopping_lists.models import ShoppingList, ShoppingListItem, ShoppingListItemSource

__all__ = [
    "ActivityProfile",
    "ApplicationRuleSet",
    "Assessment",
    "AssessmentMetric",
    "ConsentRecord",
    "DailyMealPlan",
    "DeletionRecord",
    "DietaryRestriction",
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
    "PrivacyAction",
    "ProcessingPurpose",
    "Profile",
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
]
