from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.modules.pantry import service as pantry_service
from app.modules.pantry.models import PantryLocation, PantryStockLot
from app.modules.pantry_recipe_availability.engine import DateMode, Lot, Requirement, calculate
from app.modules.recipes import repository as recipe_repository
from app.modules.recipes.models import Recipe


def _error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def _requirements(
    recipe: Recipe, include_optional: bool
) -> tuple[list[Requirement], list[dict[str, Any]]]:
    grouped: dict[UUID, dict[str, Any]] = {}
    excluded = []
    for ingredient in recipe.ingredients:
        if ingredient.is_optional and not include_optional:
            excluded.append(
                {
                    "recipe_ingredient_id": ingredient.id,
                    "food_id": ingredient.food_id,
                    "food_name": ingredient.food.name,
                    "warning": "PANTRY_AVAILABILITY_OPTIONAL_INGREDIENT_EXCLUDED",
                }
            )
            continue
        group = grouped.setdefault(
            ingredient.food_id,
            {
                "food": ingredient.food,
                "quantity": Decimal(0),
                "unit": ingredient.normalized_unit,
                "optional": ingredient.is_optional,
                "estimated": False,
                "contributions": [],
            },
        )
        if group["unit"] != ingredient.normalized_unit:
            raise _error(
                "PANTRY_AVAILABILITY_UNIT_INCOMPATIBLE",
                "Zutaten mit demselben Lebensmittel verwenden inkompatible Einheiten.",
            )
        per_portion = ingredient.normalized_quantity / recipe.servings
        group["quantity"] += per_portion
        group["estimated"] = group["estimated"] or ingredient.conversion_is_estimated
        group["contributions"].append(
            {
                "recipe_ingredient_id": ingredient.id,
                "stored_quantity": ingredient.quantity,
                "stored_unit": ingredient.unit_code,
                "normalized_quantity": ingredient.normalized_quantity,
                "normalized_unit": ingredient.normalized_unit,
                "required_per_portion": per_portion,
                "preparation_note": ingredient.preparation_note,
            }
        )
    return [
        Requirement(
            food_id=fid,
            food_name=g["food"].name,
            required_per_portion=g["quantity"],
            unit=g["unit"],
            optional=g["optional"],
            estimated=g["estimated"],
            archived_food=g["food"].is_archived,
            contributions=tuple(g["contributions"]),
        )
        for fid, g in grouped.items()
    ], excluded


def _lots(session: Session, profile_id: UUID, food_ids: set[UUID]) -> dict[UUID, list[Lot]]:
    if not food_ids:
        return {}
    rows = list(
        session.scalars(
            select(PantryStockLot)
            .join(PantryLocation)
            .where(
                PantryStockLot.owner_profile_id == profile_id,
                PantryStockLot.food_id.in_(food_ids),
                PantryStockLot.is_archived.is_(False),
                PantryStockLot.is_depleted.is_(False),
                PantryStockLot.current_quantity > 0,
                PantryLocation.is_archived.is_(False),
            )
            .options(selectinload(PantryStockLot.location))
        )
    )
    result: dict[UUID, list[Lot]] = {}
    for row in rows:
        result.setdefault(row.food_id, []).append(
            Lot(
                id=row.id,
                location_id=row.location_id,
                location_name=row.location.name,
                quantity=row.current_quantity,
                unit=row.normalized_unit,
                date_status=pantry_service.date_status(row),
                relevant_date=row.use_by_date or row.best_before_date,
                estimated=row.initial_conversion_estimated,
                updated_at=row.updated_at,
            )
        )
    return result


def availability(
    session: Session,
    profile_id: UUID,
    recipe_id: UUID,
    portions: Decimal,
    include_optional: bool,
    date_mode: DateMode,
    include_lot_details: bool = True,
) -> dict[str, Any]:
    if portions <= 0 or portions > 1000:
        raise _error(
            "PANTRY_AVAILABILITY_INVALID_PORTION_COUNT",
            "Die Portionszahl muss zwischen 0 und 1000 liegen.",
        )
    if date_mode not in {"include_all", "exclude_past_use_by", "exclude_all_past_dates"}:
        raise _error("PANTRY_AVAILABILITY_INVALID_DATE_MODE", "Der Datumsmodus ist ungültig.")
    recipe = recipe_repository.get(session, profile_id, recipe_id)
    if recipe is None:
        raise _error(
            "PANTRY_AVAILABILITY_RECIPE_NOT_FOUND", "Das Rezept wurde nicht gefunden.", 404
        )
    requirements, excluded = _requirements(recipe, include_optional)
    lots = _lots(session, profile_id, {r.food_id for r in requirements})
    result = calculate(requirements, lots, portions, date_mode)
    warnings = []
    if recipe.is_archived:
        warnings.append(
            _warning("PANTRY_AVAILABILITY_RECIPE_ARCHIVED", "Das Rezept ist archiviert.")
        )
    for req in requirements:
        if req.archived_food:
            warnings.append(
                _warning(
                    "PANTRY_AVAILABILITY_FOOD_ARCHIVED",
                    f"Das Lebensmittel „{req.food_name}“ ist archiviert.",
                )
            )
    all_lots = [lot for values in lots.values() for lot in values]
    if date_mode == "include_all" and any(
        lot.date_status == "past_best_before" for lot in all_lots
    ):
        warnings.append(
            _warning(
                "PANTRY_AVAILABILITY_PAST_BEST_BEFORE_INCLUDED",
                "Bestand mit überschrittenem Mindesthaltbarkeitsdatum wurde entsprechend "
                "der Einstellung berücksichtigt.",
            )
        )
    if date_mode == "include_all" and any(lot.date_status == "past_use_by" for lot in all_lots):
        warnings.append(
            _warning(
                "PANTRY_AVAILABILITY_PAST_USE_BY_INCLUDED",
                "Bestand mit überschrittenem Verbrauchsdatum wurde entsprechend der "
                "Einstellung berücksichtigt.",
            )
        )
    if not include_lot_details:
        for item in result["ingredients"]:
            item["lot_contributions"] = []
    counts = {
        status: sum(lot.date_status == status for lot in all_lots)
        for status in ("past_best_before", "past_use_by", "expiring_soon")
    }
    return {
        "recipe": {
            "id": recipe.id,
            "name": recipe.name,
            "stored_servings": recipe.servings,
            "is_archived": recipe.is_archived,
            "updated_at": recipe.updated_at,
        },
        "requested_portion_count": portions,
        **result,
        "excluded_optional_ingredients": excluded,
        "date_handling": {
            "mode": date_mode,
            **{f"{key}_lot_count": value for key, value in counts.items()},
        },
        "warnings": warnings,
        "calculated_at": datetime.now(UTC),
        "freshness": {
            "latest_pantry_update": max((lot.updated_at for lot in all_lots), default=None),
            "stock_is_not_reserved": True,
        },
    }


def summaries(
    session: Session,
    profile_id: UUID,
    *,
    query: str | None,
    include_archived: bool,
    state: str | None,
    minimum_portions: Decimal | None,
    sort: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    recipes, _ = recipe_repository.list_recipes(
        session,
        profile_id,
        query=query,
        tag=None,
        include_archived=include_archived,
        page=1,
        page_size=100,
    )
    rows = []
    for recipe in recipes:
        result = availability(
            session, profile_id, recipe.id, Decimal(1), False, "include_all", False
        )
        summary = result["ingredient_summary"]
        row = {
            "recipe_id": recipe.id,
            "name": recipe.name,
            "is_archived": recipe.is_archived,
            "availability_state": result["availability_state"],
            "maximum_possible_portions": result["maximum_possible_portions"],
            "required_ingredient_count": summary["required_count"],
            "available_ingredient_count": summary["fully_available_count"],
            "missing_ingredient_count": summary["partially_available_count"]
            + summary["not_available_count"],
            "unresolved_ingredient_count": summary["unresolved_count"],
            "limiting_ingredient_names": [
                i["food_name"] for i in result["limiting_ingredients"][:2]
            ],
            "calculated_at": result["calculated_at"],
        }
        if (state is None or row["availability_state"] == state) and (
            minimum_portions is None or (row["maximum_possible_portions"] or 0) >= minimum_portions
        ):
            rows.append(row)
    order = {
        "fully_available": 0,
        "partially_available": 1,
        "not_available": 2,
        "unresolved": 3,
        "empty_recipe": 4,
    }
    if sort == "maximum_possible_portions":
        rows.sort(key=lambda r: (-(r["maximum_possible_portions"] or 0), str(r["name"]).casefold()))
    elif sort == "missing_ingredient_count":
        rows.sort(key=lambda r: (r["missing_ingredient_count"], str(r["name"]).casefold()))
    elif sort == "recipe_name":
        rows.sort(key=lambda r: str(r["name"]).casefold())
    else:
        rows.sort(
            key=lambda r: (order.get(str(r["availability_state"]), 9), str(r["name"]).casefold())
        )
    total = len(rows)
    selected = rows[(page - 1) * page_size : page * page_size]
    return {
        "items": selected,
        "page": page,
        "page_size": page_size,
        "total": total,
        "portion_count": Decimal(1),
    }


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "warning", "message_de": message}
