from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.recipe_target_comparison.target_mapping import TargetKind
from app.modules.recipe_target_comparison.unit_conversion import IncompatibleUnitError, convert


@dataclass(frozen=True, slots=True)
class TargetDescriptor:
    nutrient_code: str
    display_name_de: str
    target_kind: TargetKind
    value: Decimal | None
    minimum: Decimal | None
    maximum: Decimal | None
    unit: str
    category: str
    display_order: int


@dataclass(frozen=True, slots=True)
class RecipeNutrientInput:
    nutrient_code: str
    amount_per_serving: Decimal
    unit: str
    coverage_ratio: Decimal
    known_ingredient_count: int
    relevant_ingredient_count: int
    missing_ingredients: tuple[dict[str, object], ...]
    is_complete: bool


def compare_item(
    recipe: RecipeNutrientInput | None,
    target: TargetDescriptor,
    portion_count: Decimal,
) -> dict[str, object]:
    base: dict[str, object] = {
        "nutrient_code": target.nutrient_code,
        "display_name_de": target.display_name_de,
        "category": target.category,
        "target_kind": target.target_kind,
        "target_minimum": target.minimum,
        "target_value": target.value,
        "target_maximum": target.maximum,
        "target_unit": target.unit,
        "contribution_to_min_percent": None,
        "contribution_percent": None,
        "contribution_to_max_percent": None,
        "formula_de": None,
        "limitations": [],
    }
    if recipe is None or recipe.known_ingredient_count == 0:
        return {
            **base,
            "selected_amount": None,
            "amount_per_serving": None,
            "unit": target.unit,
            "relation": "unavailable",
            "comparison_status": "unavailable",
            "coverage_ratio": Decimal(0),
            "known_ingredient_count": 0,
            "relevant_ingredient_count": 0 if recipe is None else recipe.relevant_ingredient_count,
            "missing_ingredients": [] if recipe is None else list(recipe.missing_ingredients),
            "explanation": (
                "Ein Vergleich ist nicht möglich, da keine passenden Rezeptdaten vorliegen."
            ),
        }
    selected_original = recipe.amount_per_serving * portion_count
    try:
        selected = convert(selected_original, recipe.unit, target.unit)
        per_serving = convert(recipe.amount_per_serving, recipe.unit, target.unit)
    except IncompatibleUnitError:
        return {
            **base,
            "selected_amount": selected_original,
            "amount_per_serving": recipe.amount_per_serving,
            "unit": recipe.unit,
            "relation": "unit_incompatible",
            "comparison_status": "unavailable",
            "coverage_ratio": recipe.coverage_ratio,
            "known_ingredient_count": recipe.known_ingredient_count,
            "relevant_ingredient_count": recipe.relevant_ingredient_count,
            "missing_ingredients": list(recipe.missing_ingredients),
            "explanation": (
                "Dieser Wert kann wegen nicht kompatibler Einheiten derzeit nicht "
                "verglichen werden."
            ),
            "limitations": ["TARGET_UNIT_INCOMPATIBLE"],
        }
    complete = recipe.is_complete
    status = "complete" if complete else "partial"
    prefix = "Der bekannte Beitrag" if not complete else "Die verglichene Menge"
    relation = "unavailable"
    explanation: str
    formula: str | None = None
    if target.target_kind in {"minimum", "reference"}:
        denominator = target.minimum if target.target_kind == "minimum" else target.value
        if denominator is None or denominator <= 0:
            return _invalid_target(base, recipe, selected, per_serving, target.unit)
        percent = selected / denominator * Decimal(100)
        base["contribution_percent"] = percent
        relation = (
            "meets_minimum"
            if target.target_kind == "minimum" and selected >= denominator
            else "contribution"
        )
        noun = "Mindestwert" if target.target_kind == "minimum" else "Referenzwert"
        qualifier = "mindestens " if not complete else ""
        explanation = f"{prefix} beträgt {qualifier}{_display(percent)} % des {noun}es."
        formula = f"{selected} / {denominator} mal 100 = {percent} %"
    elif target.target_kind == "maximum":
        maximum = target.maximum or target.value
        if maximum is None or maximum <= 0:
            return _invalid_target(base, recipe, selected, per_serving, target.unit)
        percent = selected / maximum * Decimal(100)
        base["contribution_percent"] = percent
        if selected > maximum:
            relation = "exceeds_limit"
            explanation = (
                f"{prefix} überschreitet bereits den Tageshöchstwert ({_display(percent)} %)."
            )
        elif not complete:
            relation = "unknown_due_to_incomplete_data"
            explanation = (
                f"Der bekannte Anteil nutzt {_display(percent)} % des Tageshöchstwertes; "
                "fehlende Werte können den Anteil erhöhen."
            )
        else:
            relation = "within_limit"
            explanation = (
                f"Die verglichene Menge nutzt {_display(percent)} % des Tageshöchstwertes."
            )
        formula = f"{selected} / {maximum} mal 100 = {percent} %"
    else:
        minimum, maximum = target.minimum, target.maximum
        if minimum is None or maximum is None or minimum <= 0 or maximum <= 0:
            return _invalid_target(base, recipe, selected, per_serving, target.unit)
        to_min = selected / minimum * Decimal(100)
        to_max = selected / maximum * Decimal(100)
        base["contribution_to_min_percent"] = to_min
        base["contribution_to_max_percent"] = to_max
        if selected > maximum:
            relation = "above_range"
        elif not complete:
            relation = "unknown_due_to_incomplete_data"
        elif selected >= minimum:
            relation = "within_range"
        else:
            relation = "below_range"
        explanation = (
            f"{prefix} entspricht {'mindestens ' if not complete else ''}"
            f"{_display(to_max)} bis {_display(to_min)} % des täglichen Zielbereichs."
        )
        formula = (
            f"{selected} / {minimum} mal 100 = {to_min} %; "
            f"{selected} / {maximum} mal 100 = {to_max} %"
        )
    limitations = [] if complete else ["RECIPE_NUTRIENT_DATA_INCOMPLETE"]
    return {
        **base,
        "selected_amount": selected,
        "amount_per_serving": per_serving,
        "unit": target.unit,
        "relation": relation,
        "comparison_status": status,
        "coverage_ratio": recipe.coverage_ratio,
        "known_ingredient_count": recipe.known_ingredient_count,
        "relevant_ingredient_count": recipe.relevant_ingredient_count,
        "missing_ingredients": list(recipe.missing_ingredients),
        "explanation": explanation,
        "formula_de": formula,
        "limitations": limitations,
    }


def _invalid_target(
    base: dict[str, object],
    recipe: RecipeNutrientInput,
    selected: Decimal,
    per_serving: Decimal,
    unit: str,
) -> dict[str, object]:
    return {
        **base,
        "selected_amount": selected,
        "amount_per_serving": per_serving,
        "unit": unit,
        "relation": "unavailable",
        "comparison_status": "unavailable",
        "coverage_ratio": recipe.coverage_ratio,
        "known_ingredient_count": recipe.known_ingredient_count,
        "relevant_ingredient_count": recipe.relevant_ingredient_count,
        "missing_ingredients": list(recipe.missing_ingredients),
        "explanation": "Der gespeicherte Zielwert ist für diesen Vergleich nicht verfügbar.",
        "limitations": ["TARGET_VALUE_INVALID"],
    }


def _display(value: Decimal) -> str:
    text = f"{value.quantize(Decimal('0.1')):f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")
