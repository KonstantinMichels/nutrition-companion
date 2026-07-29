from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.modules.foods import service as food_service
from app.modules.foods.models import Food
from app.modules.foods.nutrient_catalog import CORE_CODES, NUTRIENT_BY_CODE
from app.modules.foods.schemas import NutrientResponse
from app.modules.recipes.models import Recipe, RecipeIngredient


def calculate_recipe(recipe: Recipe) -> dict[str, Any]:
    count = len(recipe.ingredients)
    totals: dict[str, Decimal] = defaultdict(Decimal)
    known_counts: dict[str, int] = defaultdict(int)
    derived_codes: set[str] = set()
    missing: dict[str, list[dict[str, object]]] = defaultdict(list)
    theoretical_g = Decimal(0)
    weight_known = 0
    estimated = 0
    archived = 0
    all_codes = set(CORE_CODES)
    resolved: list[tuple[RecipeIngredient, dict[str, NutrientResponse]]] = []
    for ingredient in recipe.ingredients:
        food: Food = ingredient.food
        serialized = food_service.serialize(food)
        food_values = {item.nutrient_code: item for item in serialized.nutrients}
        all_codes.update(food_values)
        resolved.append((ingredient, food_values))
        estimated += int(ingredient.conversion_is_estimated)
        archived += int(food.is_archived)
        if ingredient.normalized_unit == "g":
            theoretical_g += ingredient.normalized_quantity
            weight_known += 1
        elif food.density_g_per_ml is not None:
            theoretical_g += ingredient.normalized_quantity * food.density_g_per_ml
            weight_known += 1
    for ingredient, ingredient_values in resolved:
        for code in all_codes:
            nutrient = ingredient_values.get(code)
            if nutrient is None:
                missing[code].append(
                    {
                        "ingredient_id": ingredient.id,
                        "food_id": ingredient.food_id,
                        "food_name": ingredient.food.name,
                    }
                )
                continue
            totals[code] += (
                nutrient.amount
                * ingredient.normalized_quantity
                / ingredient.food.reference_quantity
            )
            known_counts[code] += 1
            if nutrient.is_derived:
                derived_codes.add(code)
    weight_complete = count > 0 and weight_known == count
    if recipe.finished_weight_g is not None:
        weight_status, weight_g = "finished_weight", recipe.finished_weight_g
    elif weight_complete:
        weight_status, weight_g = "theoretical_complete", theoretical_g
    else:
        weight_status, weight_g = "unavailable", None
    nutrients: list[dict[str, Any]] = []
    for code in sorted(all_codes, key=lambda item: NUTRIENT_BY_CODE[item].display_order):
        definition = NUTRIENT_BY_CODE[code]
        total = totals[code]
        nutrients.append(
            {
                "nutrient_code": code,
                "display_name_de": definition.display_name_de,
                "amount_total": total,
                "amount_per_serving": total / recipe.servings,
                "amount_per_100g": None if weight_g is None else total / weight_g * Decimal(100),
                "unit": definition.canonical_unit,
                "known_ingredient_count": known_counts[code],
                "relevant_ingredient_count": count,
                "coverage_ratio": Decimal(known_counts[code]) / Decimal(count)
                if count
                else Decimal(0),
                "is_complete": known_counts[code] == count,
                "includes_derived_input": code in derived_codes,
                "missing_ingredients": missing[code],
            }
        )
    basic_complete = all(
        next(item for item in nutrients if item["nutrient_code"] == code)["is_complete"]
        for code in CORE_CODES
    )
    micro = [
        item
        for item in nutrients
        if NUTRIENT_BY_CODE[str(item["nutrient_code"])].category in {"vitamin", "mineral"}
        and item["known_ingredient_count"]
    ]
    micro_level = (
        "none"
        if not micro
        else ("complete" if all(item["is_complete"] for item in micro) else "partial")
    )
    quality_level = (
        "incomplete"
        if not basic_complete
        else ("extended" if len(micro) >= 4 else "basic_complete")
    )
    warnings = []
    if not basic_complete:
        warnings.append("Grundnährwerte sind wegen fehlender Lebensmitteldaten unvollständig.")
    if archived:
        warnings.append("Das Rezept verwendet mindestens ein archiviertes Lebensmittel.")
    if estimated:
        warnings.append("Mindestens eine Mengenumrechnung ist geschätzt.")
    if weight_g is None:
        warnings.append("Nährwerte pro 100 g sind ohne vollständiges Gewicht nicht verfügbar.")
    if not recipe.steps:
        warnings.append("Es sind keine Zubereitungsschritte angegeben.")
    return {
        "nutrients": nutrients,
        "weight": {
            "status": weight_status,
            "weight_g": weight_g,
            "theoretical_weight_g": theoretical_g,
            "coverage_ratio": Decimal(weight_known) / Decimal(count) if count else Decimal(0),
        },
        "quality": {
            "ingredient_count": count,
            "normalized_ingredient_count": count,
            "estimated_conversion_count": estimated,
            "archived_food_count": archived,
            "basic_nutrition_complete": basic_complete,
            "micronutrient_coverage_level": micro_level,
            "quality_level": quality_level,
            "warnings": warnings,
        },
    }


def scale_servings(recipe: Recipe, desired: Decimal) -> dict[str, object]:
    if desired <= 0:
        raise ValueError("desired servings must be positive")
    factor = desired / recipe.servings
    return {
        "base_servings": recipe.servings,
        "desired_servings": desired,
        "scaling_factor": factor,
        "ingredients": [
            {
                "ingredient_id": item.id,
                "food_name": item.food.name,
                "quantity": item.quantity * factor,
                "unit_code": item.unit_code,
            }
            for item in recipe.ingredients
        ],
    }
