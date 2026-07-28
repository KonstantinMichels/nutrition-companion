from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class NutrientDefinition:
    code: str
    display_name_de: str
    technical_name_en: str
    category: str
    canonical_unit: str
    display_order: int
    basic_form: bool = False
    optional: bool = True
    plausibility_max: Decimal | None = None
    active: bool = True


def _n(
    code: str,
    de: str,
    en: str,
    category: str,
    unit: str,
    order: int,
    basic: bool = False,
    maximum: str | None = None,
) -> NutrientDefinition:
    return NutrientDefinition(
        code, de, en, category, unit, order, basic, not basic, Decimal(maximum) if maximum else None
    )


NUTRIENTS = (
    _n("energy_kcal", "Energie", "Energy", "energy", "kcal", 10, True, "2000"),
    _n("energy_kj", "Energie", "Energy", "energy", "kJ", 11),
    _n("fat", "Fett", "Fat", "macronutrient", "g", 20, True, "100"),
    _n(
        "saturated_fat",
        "davon gesättigte Fettsäuren",
        "Saturated fat",
        "fat_detail",
        "g",
        21,
        True,
        "100",
    ),
    _n("carbohydrate", "Kohlenhydrate", "Carbohydrate", "macronutrient", "g", 30, True, "100"),
    _n("sugars", "davon Zucker", "Sugars", "carbohydrate_detail", "g", 31, True, "100"),
    _n("fiber", "Ballaststoffe", "Fiber", "fiber", "g", 40, True, "100"),
    _n("protein", "Eiweiß", "Protein", "macronutrient", "g", 50, True, "100"),
    _n("salt", "Salz", "Salt", "mineral", "g", 60, True, "100"),
    _n("sodium", "Natrium", "Sodium", "mineral", "g", 61),
    _n("vitamin_a", "Vitamin A", "Vitamin A", "vitamin", "µg RAE", 100),
    _n("vitamin_d", "Vitamin D", "Vitamin D", "vitamin", "µg", 110),
    _n("vitamin_e", "Vitamin E", "Vitamin E", "vitamin", "mg", 120),
    _n("vitamin_k", "Vitamin K", "Vitamin K", "vitamin", "µg", 130),
    _n("vitamin_c", "Vitamin C", "Vitamin C", "vitamin", "mg", 140),
    _n("thiamin", "Thiamin (Vitamin B1)", "Thiamin", "vitamin", "mg", 150),
    _n("riboflavin", "Riboflavin (Vitamin B2)", "Riboflavin", "vitamin", "mg", 160),
    _n("niacin", "Niacin", "Niacin", "vitamin", "mg NE", 170),
    _n("pantothenic_acid", "Pantothensäure", "Pantothenic acid", "vitamin", "mg", 180),
    _n("vitamin_b6", "Vitamin B6", "Vitamin B6", "vitamin", "mg", 190),
    _n("biotin", "Biotin", "Biotin", "vitamin", "µg", 200),
    _n("folate", "Folat", "Folate", "vitamin", "µg DFE", 210),
    _n("vitamin_b12", "Vitamin B12", "Vitamin B12", "vitamin", "µg", 220),
    _n("calcium", "Calcium", "Calcium", "mineral", "mg", 300),
    _n("magnesium", "Magnesium", "Magnesium", "mineral", "mg", 310),
    _n("potassium", "Kalium", "Potassium", "mineral", "mg", 320),
    _n("chloride", "Chlorid", "Chloride", "mineral", "mg", 340),
    _n("phosphorus", "Phosphor", "Phosphorus", "mineral", "mg", 350),
    _n("iron", "Eisen", "Iron", "mineral", "mg", 360),
    _n("zinc", "Zink", "Zinc", "mineral", "mg", 370),
    _n("iodine", "Jod", "Iodine", "mineral", "µg", 380),
    _n("selenium", "Selen", "Selenium", "mineral", "µg", 390),
    _n("copper", "Kupfer", "Copper", "mineral", "mg", 400),
    _n("manganese", "Mangan", "Manganese", "mineral", "mg", 410),
    _n("chromium", "Chrom", "Chromium", "mineral", "µg", 420),
    _n("molybdenum", "Molybdän", "Molybdenum", "mineral", "µg", 430),
)
NUTRIENT_BY_CODE = {item.code: item for item in NUTRIENTS}
CORE_CODES = frozenset({"energy_kcal", "fat", "carbohydrate", "protein"})
DERIVED_CODES = frozenset({"energy_kj", "salt", "sodium"})
