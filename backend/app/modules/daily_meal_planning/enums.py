from enum import StrEnum


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    MORNING_SNACK = "morning_snack"
    LUNCH = "lunch"
    AFTERNOON_SNACK = "afternoon_snack"
    DINNER = "dinner"
    EVENING_SNACK = "evening_snack"
    OTHER = "other"


MEAL_LABELS_DE = {
    MealType.BREAKFAST: "Frühstück",
    MealType.MORNING_SNACK: "Vormittagssnack",
    MealType.LUNCH: "Mittagessen",
    MealType.AFTERNOON_SNACK: "Nachmittagssnack",
    MealType.DINNER: "Abendessen",
    MealType.EVENING_SNACK: "Abendsnack",
    MealType.OTHER: "Andere Mahlzeit",
}


class EntryType(StrEnum):
    RECIPE = "recipe"
    FOOD = "food"
