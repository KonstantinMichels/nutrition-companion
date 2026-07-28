from enum import StrEnum


class ReferenceUnit(StrEnum):
    G = "g"
    ML = "ml"


class FoodType(StrEnum):
    USER_CREATED = "user_created"
    BRANDED = "branded"


class SourceType(StrEnum):
    USER_ENTERED = "user_entered"
    OPEN_FOOD_FACTS = "open_food_facts"
    SYSTEM_DERIVED = "system_derived"


class ValueSource(StrEnum):
    USER_ENTERED = "user_entered"
    OPEN_FOOD_FACTS = "open_food_facts"
    SYSTEM_DERIVED = "system_derived"
