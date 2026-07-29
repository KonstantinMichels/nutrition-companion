from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_FLOOR, Decimal
from typing import Any, Literal
from uuid import UUID

DateMode = Literal["include_all", "exclude_past_use_by", "exclude_all_past_dates"]


@dataclass(frozen=True)
class Requirement:
    food_id: UUID
    food_name: str
    required_per_portion: Decimal
    unit: str
    optional: bool
    estimated: bool
    archived_food: bool
    contributions: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class Lot:
    id: UUID
    location_id: UUID
    location_name: str
    quantity: Decimal
    unit: str
    date_status: str
    relevant_date: date | None
    estimated: bool
    updated_at: datetime


def calculate(
    requirements: list[Requirement],
    lots_by_food: dict[UUID, list[Lot]],
    portions: Decimal,
    date_mode: DateMode,
) -> dict[str, Any]:
    ingredients: list[dict[str, Any]] = []
    possible: list[tuple[Requirement, Decimal, Decimal, list[Lot]]] = []
    for requirement in requirements:
        required = requirement.required_per_portion * portions
        lots = [
            lot for lot in lots_by_food.get(requirement.food_id, []) if _included(lot, date_mode)
        ]
        lots.sort(key=_lot_key)
        compatible = [lot for lot in lots if lot.unit == requirement.unit]
        available = sum((lot.quantity for lot in compatible), Decimal(0))
        missing = max(required - available, Decimal(0))
        remaining = max(available - required, Decimal(0))
        state = (
            "fully_available"
            if available >= required
            else "partially_available"
            if available > 0
            else "not_available"
        )
        ratio = available / required
        allocation_left = min(required, available)
        contributions = []
        for lot in compatible:
            allocated = min(lot.quantity, allocation_left)
            allocation_left -= allocated
            contributions.append(
                {
                    "stock_lot_id": lot.id,
                    "location_id": lot.location_id,
                    "location_name": lot.location_name,
                    "available_quantity": lot.quantity,
                    "allocated_quantity": allocated,
                    "canonical_unit": lot.unit,
                    "date_status": lot.date_status,
                    "relevant_date": lot.relevant_date,
                    "conversion_estimated": lot.estimated,
                    "warning_codes": _lot_warnings(lot),
                }
            )
        per_possible = available / requirement.required_per_portion
        possible.append((requirement, per_possible, available, compatible))
        ingredients.append(
            {
                "food_id": requirement.food_id,
                "food_name": requirement.food_name,
                "required_quantity": required,
                "required_per_portion": requirement.required_per_portion,
                "available_quantity": available,
                "missing_quantity": missing,
                "hypothetical_remaining_quantity": remaining
                if state == "fully_available"
                else None,
                "coverage_ratio": ratio,
                "canonical_unit": requirement.unit,
                "availability_state": state,
                "is_optional": requirement.optional,
                "conversion_estimated": requirement.estimated,
                "archived_food": requirement.archived_food,
                "recipe_ingredient_contributions": list(requirement.contributions),
                "lot_contributions": contributions,
            }
        )
    if not requirements:
        maximum = None
        recipe_state = "empty_recipe"
        limiting: list[dict[str, Any]] = []
    else:
        maximum = min(value for _, value, _, _ in possible)
        fully = all(item["availability_state"] == "fully_available" for item in ingredients)
        any_stock = any(item["available_quantity"] > 0 for item in ingredients)
        recipe_state = (
            "fully_available"
            if fully
            else "partially_available"
            if any_stock and maximum > 0
            else "not_available"
        )
        limiting = []
        next_whole = maximum.to_integral_value(rounding=ROUND_FLOOR) + 1
        for requirement, value, available, lots in possible:
            if value == maximum:
                limiting.append(
                    {
                        "food_id": requirement.food_id,
                        "food_name": requirement.food_name,
                        "available_quantity": available,
                        "required_quantity_per_portion": requirement.required_per_portion,
                        "possible_portion_count": value,
                        "missing_for_next_complete_portion": max(
                            requirement.required_per_portion * next_whole - available, Decimal(0)
                        ),
                        "canonical_unit": requirement.unit,
                        "locations": sorted({lot.location_name for lot in lots}),
                    }
                )
    summary = {
        "required_count": len(ingredients),
        "fully_available_count": sum(
            i["availability_state"] == "fully_available" for i in ingredients
        ),
        "partially_available_count": sum(
            i["availability_state"] == "partially_available" for i in ingredients
        ),
        "not_available_count": sum(i["availability_state"] == "not_available" for i in ingredients),
        "unresolved_count": 0,
    }
    return {
        "availability_state": recipe_state,
        "maximum_possible_portions": maximum,
        "maximum_complete_whole_portions": None
        if maximum is None
        else int(maximum.to_integral_value(rounding=ROUND_FLOOR)),
        "ingredient_summary": summary,
        "ingredients": ingredients,
        "limiting_ingredients": limiting,
    }


def _included(lot: Lot, mode: DateMode) -> bool:
    if mode == "exclude_past_use_by" and lot.date_status == "past_use_by":
        return False
    return not (
        mode == "exclude_all_past_dates" and lot.date_status in {"past_use_by", "past_best_before"}
    )


def _lot_key(lot: Lot) -> tuple[int, str, str]:
    priority = {
        "date_today": 0,
        "expiring_soon": 1,
        "valid": 2,
        "no_date": 3,
        "past_best_before": 4,
        "past_use_by": 5,
    }
    return priority.get(lot.date_status, 6), str(lot.relevant_date or "9999-12-31"), str(lot.id)


def _lot_warnings(lot: Lot) -> list[str]:
    return {
        "past_best_before": ["PANTRY_AVAILABILITY_PAST_BEST_BEFORE_INCLUDED"],
        "past_use_by": ["PANTRY_AVAILABILITY_PAST_USE_BY_INCLUDED"],
    }.get(lot.date_status, [])
