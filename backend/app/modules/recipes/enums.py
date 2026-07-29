from enum import StrEnum


class IngredientUnitType(StrEnum):
    BASE = "base"
    MEASURE = "measure"


RECIPE_TAGS = {
    "breakfast": "Frühstück",
    "lunch": "Mittagessen",
    "dinner": "Abendessen",
    "snack": "Snack",
    "vegetarian": "Vegetarisch",
    "vegan": "Vegan",
    "high_protein": "Proteinreich",
    "quick": "Schnell",
    "meal_prep": "Meal Prep",
    "budget_friendly": "Preiswert",
    "prepared_food": "Fertiggericht",
}
