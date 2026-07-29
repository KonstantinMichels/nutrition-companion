from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import cast
from uuid import UUID

from app.modules.foods.nutrient_catalog import CORE_CODES, NUTRIENT_BY_CODE
from app.modules.recipe_target_comparison.engine import TargetDescriptor
from app.modules.recipe_target_comparison.unit_conversion import IncompatibleUnitError, convert


@dataclass(frozen=True, slots=True)
class ComponentValue:
    nutrient_code: str
    amount: Decimal
    unit: str
    known_count: int
    relevant_count: int
    missing_sources: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class EntryInput:
    entry_id: UUID | None
    position: int
    entry_type: str
    source_id: UUID
    source_name: str
    source_brand: str | None
    is_archived: bool
    recipe_portion_count: Decimal | None
    food_quantity: Decimal | None
    food_unit_code: str | None
    food_measure_id: UUID | None
    normalized_quantity: Decimal | None
    normalized_unit: str | None
    conversion_is_estimated: bool
    note: str | None
    nutrients: tuple[ComponentValue, ...]
    warnings: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class MealInput:
    meal_id: UUID | None
    position: int
    meal_type: str
    meal_name: str
    planned_time: object | None
    notes: str | None
    entries: tuple[EntryInput, ...]


def _aggregate(entries: tuple[EntryInput, ...]) -> list[dict[str, object]]:
    codes = set(CORE_CODES)
    for entry in entries:
        codes.update(value.nutrient_code for value in entry.nutrients)
    output: list[dict[str, object]] = []
    for code in sorted(codes, key=lambda item: NUTRIENT_BY_CODE[item].display_order):
        definition = NUTRIENT_BY_CODE[code]
        values = [
            value for entry in entries for value in entry.nutrients if value.nutrient_code == code
        ]
        relevant = sum(value.relevant_count for value in values)
        # A direct entry without this nutrient contributes one unknown source. Recipe
        # inputs already carry their complete ingredient-level denominator.
        for entry in entries:
            if not any(value.nutrient_code == code for value in entry.nutrients):
                relevant += 1
        known = sum(value.known_count for value in values)
        amount = sum((value.amount for value in values), Decimal(0)) if known else None
        missing = [item for value in values for item in value.missing_sources]
        for entry in entries:
            if not any(value.nutrient_code == code for value in entry.nutrients):
                missing.append(
                    {
                        "meal_name": "",
                        "entry_name": entry.source_name,
                        "source_name": entry.source_name,
                    }
                )
        ratio = Decimal(known) / Decimal(relevant) if relevant else None
        output.append(
            {
                "nutrient_code": code,
                "display_name_de": definition.display_name_de,
                "category": definition.category,
                "amount": amount,
                "unit": definition.canonical_unit,
                "known_component_count": known,
                "relevant_component_count": relevant,
                "coverage_ratio": ratio,
                "is_complete": relevant > 0 and known == relevant,
                "missing_sources": missing,
            }
        )
    return output


def calculate(meals: tuple[MealInput, ...]) -> dict[str, object]:
    meal_results: list[dict[str, object]] = []
    all_entries: list[EntryInput] = []
    warnings: list[dict[str, object]] = []
    for meal in meals:
        totals = _aggregate(meal.entries)
        for item in totals:
            for missing in cast(list[dict[str, str]], item["missing_sources"]):
                missing["meal_name"] = meal.meal_name
        entry_results = [_entry_dict(entry) for entry in meal.entries]
        meal_warnings = [warning for entry in meal.entries for warning in entry.warnings]
        warnings.extend(meal_warnings)
        meal_results.append(
            {
                "id": meal.meal_id,
                "position": meal.position,
                "meal_type": meal.meal_type,
                "meal_name": meal.meal_name,
                "planned_time": meal.planned_time,
                "notes": meal.notes,
                "entry_count": len(meal.entries),
                "entries": entry_results,
                "nutrient_totals": totals,
                "basic_nutrition_complete": _basic_complete(totals),
                "warnings": meal_warnings,
            }
        )
        all_entries.extend(meal.entries)
    daily = _aggregate(tuple(all_entries))
    # Fill meal names from the entry's parent where the daily aggregation rebuilt a missing item.
    entry_meal = {entry.source_name: meal.meal_name for meal in meals for entry in meal.entries}
    for total in daily:
        for missing in cast(list[dict[str, str]], total["missing_sources"]):
            missing["meal_name"] = entry_meal.get(missing["entry_name"], "Tagesplan")
    count = len(all_entries)
    basic_complete = count > 0 and _basic_complete(daily)
    micro = [
        item
        for item in daily
        if item["category"] in {"vitamin", "mineral"} and item["known_component_count"]
    ]
    micro_level = (
        "none"
        if not micro
        else ("complete" if all(item["is_complete"] for item in micro) else "partial")
    )
    quality_level = (
        "empty"
        if not count
        else (
            "incomplete"
            if not basic_complete
            else ("extended" if len(micro) >= 4 else "basic_complete")
        )
    )
    if not count:
        warnings.append(
            _warning("EMPTY_DAILY_PLAN", "info", "Der Tagesplan enthält noch keine Einträge.")
        )
    elif not basic_complete:
        warnings.append(
            _warning(
                "INCOMPLETE_BASIC_NUTRITION",
                "warning",
                "Die Grundnährwerte des Tagesplans sind wegen fehlender Quelldaten unvollständig.",
            )
        )
    quality = {
        "meal_count": len(meals),
        "entry_count": count,
        "recipe_entry_count": sum(entry.entry_type == "recipe" for entry in all_entries),
        "food_entry_count": sum(entry.entry_type == "food" for entry in all_entries),
        "normalized_entry_count": sum(
            entry.normalized_quantity is not None for entry in all_entries
        ),
        "estimated_conversion_count": sum(entry.conversion_is_estimated for entry in all_entries),
        "archived_recipe_count": sum(
            entry.entry_type == "recipe" and entry.is_archived for entry in all_entries
        ),
        "archived_food_count": sum(
            entry.entry_type == "food" and entry.is_archived for entry in all_entries
        ),
        "basic_nutrition_complete": basic_complete,
        "micronutrient_coverage_level": micro_level,
        "quality_level": quality_level,
    }
    return {"meals": meal_results, "daily_totals": daily, "quality": quality, "warnings": warnings}


def compare_targets(
    totals: list[dict[str, object]], targets: list[TargetDescriptor]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_code = {str(item["nutrient_code"]): item for item in totals}
    results: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    for target in targets:
        source = by_code.get(target.nutrient_code)
        result = _compare_target(source, target)
        results.append(result)
        if result["relation"] == "unit_incompatible":
            warnings.append(
                _warning(
                    "TARGET_UNIT_INCOMPATIBLE",
                    "warning",
                    f"{target.display_name_de} kann wegen nicht kompatibler Einheiten "
                    "nicht verglichen werden.",
                    nutrient_code=target.nutrient_code,
                )
            )
        if result["relation"] == "exceeds_limit":
            warnings.append(
                _warning(
                    "KNOWN_AMOUNT_EXCEEDS_MAXIMUM",
                    "warning",
                    f"Der bekannte geplante Wert für {target.display_name_de} überschreitet "
                    "den Tageshöchstwert.",
                    nutrient_code=target.nutrient_code,
                )
            )
        if result["relation"] == "above_range":
            warnings.append(
                _warning(
                    "DAILY_VALUE_ABOVE_TARGET_RANGE",
                    "warning",
                    f"Der bekannte geplante Wert für {target.display_name_de} liegt über "
                    "dem Zielbereich.",
                    nutrient_code=target.nutrient_code,
                )
            )
    return results, warnings


def _compare_target(
    source: dict[str, object] | None, target: TargetDescriptor
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
        "contribution_percent": None,
        "contribution_to_min_percent": None,
        "contribution_to_max_percent": None,
        "remaining_amount": None,
        "remaining_kind": None,
        "remaining_status": None,
    }
    if source is None or source["amount"] is None:
        return {
            **base,
            "amount": None,
            "unit": target.unit,
            "relation": "unavailable",
            "comparison_status": "unavailable",
            "explanation_de": "Für diesen Nährstoff liegen keine geplanten Werte vor.",
            "coverage_ratio": None,
        }
    amount = cast(Decimal, source["amount"])
    unit = str(source["unit"])
    try:
        amount = convert(amount, unit, target.unit)
    except IncompatibleUnitError:
        return {
            **base,
            "amount": amount,
            "unit": unit,
            "relation": "unit_incompatible",
            "comparison_status": "unavailable",
            "explanation_de": "Die Einheiten sind nicht kompatibel.",
            "coverage_ratio": source["coverage_ratio"],
        }
    complete = bool(source["is_complete"])
    status = "complete" if complete else "partial"
    kind = target.target_kind
    relation = "unavailable"
    explanation = ""
    remaining: Decimal | None = None
    remaining_kind: str | None = None
    remaining_status: str | None = "exact" if complete else "upper_bound_only"
    if kind == "minimum":
        threshold = target.minimum or target.value
        if threshold is not None and threshold > 0:
            base["contribution_percent"] = amount / threshold * Decimal(100)
            relation = (
                "meets_minimum"
                if amount >= threshold
                else ("below_minimum" if complete else "indeterminate")
            )
            remaining = max(threshold - amount, Decimal(0))
            remaining_kind = "to_minimum"
            if amount >= threshold:
                remaining_status = "exact"
            explanation = (
                "Der Tagesplan erreicht den Mindestwert."
                if amount >= threshold
                else (
                    "Der geplante Wert liegt unter dem hinterlegten Mindestwert."
                    if complete
                    else "Auf Basis der bekannten Daten ist der genaue Abstand zum "
                    "Mindestwert ungewiss."
                )
            )
    elif kind == "maximum":
        threshold = target.maximum or target.value
        if threshold is not None and threshold > 0:
            base["contribution_percent"] = amount / threshold * Decimal(100)
            relation = (
                "exceeds_limit"
                if amount > threshold
                else (
                    "at_limit"
                    if complete and amount == threshold
                    else ("within_limit" if complete else "indeterminate")
                )
            )
            remaining = abs(threshold - amount)
            remaining_kind = "exceeded_by" if amount > threshold else "allowance"
            if amount > threshold:
                remaining_status = "exact"
            explanation = (
                "Der geplante Wert liegt über dem hinterlegten Tageshöchstwert."
                if amount > threshold
                else (
                    "Der geplante Wert liegt innerhalb des Tageshöchstwertes."
                    if complete
                    else "Der verbleibende Spielraum ist wegen fehlender Daten ungewiss."
                )
            )
    elif kind == "range":
        minimum, maximum = target.minimum, target.maximum
        if minimum is not None and maximum is not None and minimum > 0 and maximum > 0:
            base["contribution_to_min_percent"] = amount / minimum * Decimal(100)
            base["contribution_to_max_percent"] = amount / maximum * Decimal(100)
            if amount > maximum:
                relation, remaining, remaining_kind, remaining_status = (
                    "above_range",
                    amount - maximum,
                    "above_maximum",
                    "exact",
                )
                explanation = "Der geplante Wert liegt über der Obergrenze des Zielbereichs."
            elif not complete:
                relation, remaining, remaining_kind = (
                    "indeterminate",
                    max(minimum - amount, Decimal(0)),
                    "known_distance_to_minimum",
                )
                explanation = "Die genaue Lage im Zielbereich ist wegen fehlender Daten ungewiss."
            elif amount < minimum:
                relation, remaining, remaining_kind = "below_range", minimum - amount, "to_minimum"
                explanation = "Der geplante Wert liegt unter der Untergrenze des Zielbereichs."
            else:
                relation, remaining, remaining_kind = (
                    "within_range",
                    maximum - amount,
                    "allowance_to_maximum",
                )
                explanation = "Der geplante Wert liegt innerhalb des Zielbereichs."
    else:
        threshold = target.value
        if threshold is not None and threshold > 0:
            base["contribution_percent"] = amount / threshold * Decimal(100)
            relation = (
                "above_reference"
                if amount > threshold
                else (
                    "at_reference"
                    if complete and amount == threshold
                    else ("below_reference" if complete else "indeterminate")
                )
            )
            remaining = threshold - amount
            remaining_kind = "difference_to_reference"
            explanation = (
                "Der Referenzwert dient der neutralen Einordnung des bekannten geplanten Wertes."
            )
    return {
        **base,
        "amount": amount,
        "unit": target.unit,
        "relation": relation,
        "comparison_status": status,
        "remaining_amount": remaining,
        "remaining_kind": remaining_kind,
        "remaining_status": remaining_status,
        "explanation_de": explanation,
        "coverage_ratio": source["coverage_ratio"],
    }


def _entry_dict(entry: EntryInput) -> dict[str, object]:
    return {
        "id": entry.entry_id,
        "position": entry.position,
        "entry_type": entry.entry_type,
        "source_id": entry.source_id,
        "source_name": entry.source_name,
        "source_brand": entry.source_brand,
        "is_archived": entry.is_archived,
        "recipe_portion_count": entry.recipe_portion_count,
        "food_quantity": entry.food_quantity,
        "food_unit_code": entry.food_unit_code,
        "food_measure_id": entry.food_measure_id,
        "normalized_quantity": entry.normalized_quantity,
        "normalized_unit": entry.normalized_unit,
        "conversion_is_estimated": entry.conversion_is_estimated,
        "note": entry.note,
        "nutrient_totals": _aggregate((entry,)),
        "warnings": list(entry.warnings),
    }


def _basic_complete(totals: list[dict[str, object]]) -> bool:
    by_code = {str(item["nutrient_code"]): item for item in totals}
    return all(code in by_code and bool(by_code[code]["is_complete"]) for code in CORE_CODES)


def _warning(
    code: str, severity: str, explanation: str, *, nutrient_code: str | None = None
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "explanation_de": explanation,
        "meal_id": None,
        "entry_id": None,
        "nutrient_code": nutrient_code,
        "suggested_action_de": None,
    }
