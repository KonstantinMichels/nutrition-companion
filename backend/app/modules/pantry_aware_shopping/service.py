from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.database.base import utc_now
from app.modules.pantry import service as pantry_service
from app.modules.pantry.models import PantryLocation, PantryStockLot
from app.modules.pantry_aware_shopping.engine import calculate_target, override_relation
from app.modules.pantry_aware_shopping.models import PantryAwareShoppingOperation
from app.modules.pantry_aware_shopping.schemas import ApplyRequest, PreviewRequest
from app.modules.pantry_recipe_availability import service as recipe_availability
from app.modules.recipes import repository as recipe_repository
from app.modules.shopping_lists import service as shopping_service
from app.modules.shopping_lists.models import ShoppingList, ShoppingListItem, ShoppingListItemSource
from app.modules.shopping_lists.schemas import GenerationRequest


def _error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def _identity(source: dict[str, Any]) -> str:
    if source.get("source_identity"):
        return str(source["source_identity"])
    plan = source.get("daily_plan_id")
    entry = source.get("meal_entry_id")
    ingredient = source.get("recipe_ingredient_id")
    base = f"daily_plan:{plan}:meal_entry:{entry}"
    return f"{base}:recipe_ingredient:{ingredient}" if ingredient else base


def _version(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _extract_plan(
    session: Session, profile_id: UUID, request: PreviewRequest
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    generation = GenerationRequest(
        daily_plan_id=request.daily_plan_id,
        week_anchor_date=request.week_anchor_date,
        pantry_considered=False,
    )
    result = shopping_service.calculate(session, profile_id, generation)
    rows = []
    for item in result["items"]:
        sources = []
        for source in item["sources"]:
            source = dict(source)
            source["source_identity"] = _identity(source)
            sources.append(source)
        rows.append({**item, "sources": sources})
    reference = {
        "daily_plan_id": request.daily_plan_id,
        "week_start": result["source_week_start"],
        "week_end": result["source_week_end"],
        "planned_day_count": result["quality_summary"]["planned_day_count"],
    }
    return rows, result["unresolved_requirements"], reference


def _extract_recipe(
    session: Session, profile_id: UUID, request: PreviewRequest
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    assert request.recipe_id is not None and request.source_occurrence_id is not None
    recipe = recipe_repository.get(session, profile_id, request.recipe_id)
    if recipe is None:
        raise _error("PANTRY_AWARE_SOURCE_NOT_FOUND", "Das Rezept wurde nicht gefunden.", 404)
    requirements, excluded = recipe_availability._requirements(
        recipe, request.include_optional_recipe_ingredients
    )
    rows = []
    for req in requirements:
        sources = []
        for contribution in req.contributions:
            ingredient_id = contribution["recipe_ingredient_id"]
            sources.append(
                {
                    "source_type": "recipe_ingredient",
                    "source_identity": (
                        f"recipe:{recipe.id}:request:{request.source_occurrence_id}:"
                        f"ingredient:{ingredient_id}"
                    ),
                    "daily_plan_id": None,
                    "plan_date": None,
                    "meal_id": None,
                    "meal_name": None,
                    "meal_entry_id": None,
                    "recipe_id": recipe.id,
                    "recipe_name": recipe.name,
                    "recipe_ingredient_id": ingredient_id,
                    "quantity": Decimal(str(contribution["required_per_portion"]))
                    * request.recipe_portion_count,
                    "unit": req.unit,
                    "conversion_estimated": req.estimated,
                }
            )
        rows.append(
            {
                "food_id": req.food_id,
                "food_name": req.food_name,
                "category_code": shopping_service._category(
                    next(item.food for item in recipe.ingredients if item.food_id == req.food_id)
                ),
                "required_quantity": req.required_per_portion * request.recipe_portion_count,
                "canonical_unit": req.unit,
                "archived_food": req.archived_food,
                "sources": sources,
            }
        )
    unresolved = [
        {
            "reason_code": "PANTRY_AWARE_OPTIONAL_EXCLUDED",
            "explanation": "Eine optionale Zutat wurde entsprechend der Einstellung ausgelassen.",
            **item,
        }
        for item in excluded
    ]
    return (
        rows,
        unresolved,
        {
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "portion_count": request.recipe_portion_count,
            "archived": recipe.is_archived,
        },
    )


def _extract_reconciliation(
    session: Session, profile_id: UUID, request: PreviewRequest
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    assert request.target_shopping_list_id is not None
    target = _target(session, profile_id, request.target_shopping_list_id)
    if target.source_type == "daily_plan" and target.source_daily_plan_id:
        return _extract_plan(
            session,
            profile_id,
            request.model_copy(
                update={"source_type": "daily_plan", "daily_plan_id": target.source_daily_plan_id}
            ),
        )
    if target.source_type == "weekly_plan" and target.source_week_start:
        return _extract_plan(
            session,
            profile_id,
            request.model_copy(
                update={"source_type": "weekly_plan", "week_anchor_date": target.source_week_start}
            ),
        )
    grouped: dict[UUID, dict[str, Any]] = {}
    for item in target.items:
        for source in item.sources:
            group = grouped.setdefault(
                source.food_id,
                {
                    "food_id": source.food_id,
                    "food_name": item.food_name_snapshot or "Lebensmittel",
                    "category_code": item.category_code,
                    "required_quantity": Decimal(0),
                    "canonical_unit": source.unit,
                    "archived_food": False,
                    "sources": [],
                },
            )
            if group["canonical_unit"] != source.unit:
                continue
            group["required_quantity"] += source.quantity
            group["sources"].append(_source_dict(source))
    return list(grouped.values()), [], {"shopping_list_id": target.id, "name": target.name}


def _source_dict(source: ShoppingListItemSource) -> dict[str, Any]:
    return {
        "source_type": source.source_type,
        "source_identity": source.source_identity or _identity(source.__dict__),
        "daily_plan_id": source.daily_plan_id,
        "plan_date": source.plan_date,
        "meal_id": source.meal_id,
        "meal_name": source.meal_name_snapshot,
        "meal_entry_id": source.meal_entry_id,
        "recipe_id": source.recipe_id,
        "recipe_name": source.recipe_name_snapshot,
        "recipe_ingredient_id": source.recipe_ingredient_id,
        "quantity": source.quantity,
        "unit": source.unit,
        "conversion_estimated": source.conversion_estimated,
    }


def _extract(
    session: Session, profile_id: UUID, request: PreviewRequest
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if request.source_type == "recipe":
        return _extract_recipe(session, profile_id, request)
    if request.source_type in {"daily_plan", "weekly_plan"}:
        return _extract_plan(session, profile_id, request)
    return _extract_reconciliation(session, profile_id, request)


LOAD = (
    selectinload(ShoppingList.items).selectinload(ShoppingListItem.sources),
    selectinload(ShoppingList.items).selectinload(ShoppingListItem.food),
)


def _target(session: Session, profile_id: UUID, target_id: UUID) -> ShoppingList:
    target = session.scalar(
        select(ShoppingList)
        .where(ShoppingList.id == target_id, ShoppingList.owner_profile_id == profile_id)
        .options(*LOAD)
    )
    if target is None:
        raise _error(
            "PANTRY_AWARE_TARGET_LIST_NOT_FOUND", "Die Einkaufsliste wurde nicht gefunden.", 404
        )
    if target.is_archived:
        raise _error(
            "PANTRY_AWARE_TARGET_LIST_ARCHIVED",
            "Die Einkaufsliste muss zuerst wiederhergestellt werden.",
            409,
        )
    if target.status != "open":
        raise _error(
            "PANTRY_AWARE_TARGET_LIST_COMPLETED",
            "Die Einkaufsliste muss zuerst wieder geöffnet werden.",
            409,
        )
    return target


def eligible_lists(session: Session, profile_id: UUID) -> dict[str, Any]:
    lists = list(
        session.scalars(
            select(ShoppingList)
            .where(ShoppingList.owner_profile_id == profile_id)
            .options(selectinload(ShoppingList.items))
            .order_by(ShoppingList.updated_at.desc())
        )
    )
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "status": item.status,
                "is_archived": item.is_archived,
                "item_count": len(item.items),
                "eligible": item.status == "open" and not item.is_archived,
            }
            for item in lists
        ]
    }


def _pantry(
    session: Session, profile_id: UUID, food_ids: set[UUID], mode: str
) -> dict[UUID, dict[str, Any]]:
    rows = (
        list(
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
        if food_ids
        else []
    )
    output: dict[UUID, dict[str, Any]] = {}
    for lot in rows:
        status = pantry_service.date_status(lot)
        included = not (
            (mode == "exclude_past_use_by" and status == "past_use_by")
            or (mode == "exclude_all_past_dates" and status in {"past_use_by", "past_best_before"})
        )
        row = output.setdefault(
            lot.food_id,
            {
                "available": Decimal(0),
                "unit": lot.normalized_unit,
                "lot_count": 0,
                "locations": set(),
                "date_quantities": {},
                "latest_update": None,
            },
        )
        row["lot_count"] += 1
        row["locations"].add(lot.location.name)
        row["date_quantities"][status] = (
            row["date_quantities"].get(status, Decimal(0)) + lot.current_quantity
        )
        if included:
            row["available"] += lot.current_quantity
        if row["latest_update"] is None or lot.updated_at > row["latest_update"]:
            row["latest_update"] = lot.updated_at
    return output


def _lists(session: Session, profile_id: UUID) -> list[ShoppingList]:
    return list(
        session.scalars(
            select(ShoppingList).where(ShoppingList.owner_profile_id == profile_id).options(*LOAD)
        )
    )


def preview(session: Session, profile_id: UUID, request: PreviewRequest) -> dict[str, Any]:
    target = (
        _target(session, profile_id, request.target_shopping_list_id)
        if request.target_shopping_list_id
        else None
    )
    extracted, unresolved, reference = _extract(session, profile_id, request)
    excluded_food_ids = set(request.excluded_food_ids)
    extracted = [row for row in extracted if row["food_id"] not in excluded_food_ids]
    source_version = _version(extracted)
    all_lists = _lists(session, profile_id)
    all_sources = [
        (shopping, item, source)
        for shopping in all_lists
        for item in shopping.items
        for source in item.sources
    ]
    selected_identities = {s["source_identity"] for row in extracted for s in row["sources"]}
    representations: dict[str, list[dict[str, Any]]] = {}
    for shopping, item, source in all_sources:
        identity = source.source_identity
        if identity and identity in selected_identities:
            representations.setdefault(identity, []).append(
                {
                    "shopping_list_id": shopping.id,
                    "shopping_list_name": shopping.name,
                    "status": shopping.status,
                    "is_archived": shopping.is_archived,
                    "on_target": target is not None and shopping.id == target.id,
                    "item_id": item.id,
                }
            )
    accepted = set(request.intentional_duplicate_source_ids)
    new_by_food: dict[UUID, dict[str, Any]] = {}
    duplicate_count = 0
    for row in extracted:
        sources = []
        required = Decimal(0)
        for source in row["sources"]:
            duplicate_open = [
                rep
                for rep in representations.get(source["source_identity"], [])
                if rep["status"] == "open" and not rep["is_archived"]
            ]
            if duplicate_open and source["source_identity"] not in accepted:
                duplicate_count += 1
                continue
            required += Decimal(str(source["quantity"]))
            sources.append(source)
        if not sources:
            continue
        group = new_by_food.setdefault(
            row["food_id"],
            {**row, "required_quantity": Decimal(0), "sources": [], "duplicates": []},
        )
        group["required_quantity"] += required
        group["sources"].extend(sources)
        group["duplicates"].extend(
            rep
            for source in row["sources"]
            for rep in representations.get(source["source_identity"], [])
        )

    food_ids = set(new_by_food)
    for shopping in all_lists:
        if shopping.status == "open" and not shopping.is_archived:
            food_ids.update(i.food_id for i in shopping.items if i.food_id)
    pantry = _pantry(session, profile_id, food_ids, request.pantry_date_mode)
    existing_requirements: dict[UUID, Decimal] = {}
    commitments: dict[UUID, list[dict[str, Any]]] = {}
    for shopping in all_lists:
        if shopping.status != "open" or shopping.is_archived:
            continue
        for item in shopping.items:
            if item.food_id is None or item.canonical_unit is None:
                continue
            existing_requirements[item.food_id] = existing_requirements.get(
                item.food_id, Decimal(0)
            ) + sum((source.quantity for source in item.sources), Decimal(0))
            remaining = Decimal(0)
            if item.pantry_handoff_state != "completed":
                remaining = max(
                    (item.purchase_quantity or Decimal(0)) - item.pantry_transferred_quantity,
                    Decimal(0),
                )
            commitments.setdefault(item.food_id, []).append(
                {
                    "shopping_list_id": shopping.id,
                    "shopping_list_name": shopping.name,
                    "shopping_list_status": shopping.status,
                    "item_id": item.id,
                    "quantity": item.purchase_quantity or Decimal(0),
                    "remaining_commitment": remaining,
                    "checked": item.is_checked,
                    "handoff_state": item.pantry_handoff_state,
                    "transferred_quantity": item.pantry_transferred_quantity,
                    "is_target": target is not None and shopping.id == target.id,
                }
            )

    items = []
    for food_id, selected in new_by_food.items():
        matches = [i for i in (target.items if target else []) if i.food_id == food_id]
        generated = [i for i in matches if i.origin_type == "generated"]
        manual = [i for i in matches if i.origin_type == "manual"]
        target_item = generated[0] if len(generated) == 1 else None
        match_state = (
            "no_matching_item"
            if not matches
            else "one_generated_match"
            if len(matches) == 1 and generated
            else "one_manual_food_match"
            if len(matches) == 1 and manual
            else "multiple_matching_items"
        )
        target_commitment = sum(
            (c["remaining_commitment"] for c in commitments.get(food_id, []) if c["is_target"]),
            Decimal(0),
        )
        other_commitment = (
            sum(
                (
                    c["remaining_commitment"]
                    for c in commitments.get(food_id, [])
                    if not c["is_target"]
                ),
                Decimal(0),
            )
            if request.include_other_open_lists
            else Decimal(0)
        )
        combined = existing_requirements.get(food_id, Decimal(0)) + selected["required_quantity"]
        pantry_row = pantry.get(food_id, {})
        available = pantry_row.get("available", Decimal(0))
        calculation = calculate_target(
            combined_requirement=combined,
            pantry_available=available,
            target_commitment=target_commitment,
            other_commitment=other_commitment,
        )
        overridden = bool(target_item and target_item.quantity_overridden)
        items.append(
            {
                "food_id": food_id,
                "food_name": selected["food_name"],
                "category_code": selected["category_code"],
                "canonical_unit": selected["canonical_unit"],
                "new_selected_requirement": selected["required_quantity"],
                "existing_open_linked_requirement": existing_requirements.get(food_id, Decimal(0)),
                "combined_requirement": combined,
                "pantry_available": available,
                "pantry_detail": {
                    **pantry_row,
                    "locations": sorted(pantry_row.get("locations", set())),
                },
                "other_open_list_commitment": other_commitment,
                "target_existing_commitment": target_commitment,
                **calculation,
                "target_item_state": match_state,
                "target_item_id": target_item.id if target_item else None,
                "quantity_overridden": overridden,
                "current_purchase_quantity": target_item.purchase_quantity if target_item else None,
                "override_relation": override_relation(
                    target_item.purchase_quantity if target_item else None,
                    calculation["desired_target_commitment"],
                )
                if overridden
                else None,
                "source_contributions": selected["sources"],
                "source_duplicates": selected["duplicates"],
                "other_list_details": [
                    c for c in commitments.get(food_id, []) if not c["is_target"]
                ],
                "warnings": ["PANTRY_AWARE_QUANTITY_OVERRIDE_PRESERVED" for _ in [0] if overridden]
                + (
                    ["PANTRY_AWARE_MANUAL_ITEM_CONFLICT"]
                    if match_state == "one_manual_food_match"
                    else []
                )
                + (
                    ["PANTRY_AWARE_MULTIPLE_ITEM_MATCHES"]
                    if match_state == "multiple_matching_items"
                    else []
                ),
            }
        )
    items.sort(key=lambda row: (row["category_code"], row["food_name"].casefold()))
    summary = {
        "food_count": len(items),
        "item_create_count": sum(i["target_change_state"] == "create" for i in items),
        "item_update_count": sum(
            i["target_change_state"] in {"increase", "decrease"} for i in items
        ),
        "unchanged_count": sum(i["target_change_state"] == "unchanged" for i in items),
        "override_conflict_count": sum(i["quantity_overridden"] for i in items),
        "duplicate_source_count": duplicate_count,
        "unresolved_requirement_count": len(unresolved),
    }
    result: dict[str, Any] = {
        "source": {
            "type": request.source_type,
            "reference": reference,
            "source_version": source_version,
        },
        "target_list": None
        if target is None
        else {
            "id": target.id,
            "name": target.name,
            "status": target.status,
            "version": target.version,
        },
        "new_list": {"name": request.new_list_name} if request.create_new_list else None,
        "items": items,
        "unresolved_requirements": unresolved,
        "duplicate_sources": [
            {"source_identity": identity, "representations": values}
            for identity, values in representations.items()
            if any(value["status"] == "open" and not value["is_archived"] for value in values)
        ],
        "summary": summary,
        "assumptions": [
            "Aktueller Vorrat wurde berücksichtigt.",
            "Offene Einkaufslisten wurden berücksichtigt."
            if request.include_other_open_lists
            else "Andere offene Einkaufslisten wurden nicht berücksichtigt.",
            "Abgeschlossene Einkaufslisten wurden nicht berücksichtigt.",
            "Der Vorrat wurde nicht reserviert.",
            "Manuell angepasste Mengen werden nicht überschrieben.",
        ],
        "warnings": [],
        "calculated_at": datetime.now(UTC),
    }
    result["preview_token"] = _version(
        {key: value for key, value in result.items() if key != "calculated_at"}
    )
    return result


def apply(session: Session, profile_id: UUID, payload: ApplyRequest) -> dict[str, Any]:
    existing = session.scalar(
        select(PantryAwareShoppingOperation).where(
            PantryAwareShoppingOperation.owner_profile_id == profile_id,
            PantryAwareShoppingOperation.client_operation_id == payload.client_operation_id,
        )
    )
    if existing:
        return {
            "operation_id": existing.id,
            "target_shopping_list_id": existing.target_shopping_list_id,
            "summary": existing.result_summary,
            "idempotent_replay": True,
        }
    calculated = preview(session, profile_id, payload.preview)
    if calculated["preview_token"] != payload.preview_token:
        raise _error(
            "PANTRY_AWARE_SHOPPING_PREVIEW_STALE",
            "Die Vorschau ist nicht mehr aktuell. Bitte berechne sie erneut.",
            409,
        )
    try:
        if payload.preview.create_new_list:
            target = ShoppingList(
                owner_profile_id=profile_id,
                name=payload.preview.new_list_name or "Einkauf",
                source_type="mixed",
                pantry_considered=True,
                source_summary={"quality_level": "pantry_aware"},
            )
            session.add(target)
            session.flush()
        else:
            assert payload.preview.target_shopping_list_id is not None
            target = _target(session, profile_id, payload.preview.target_shopping_list_id)
        operation = PantryAwareShoppingOperation(
            owner_profile_id=profile_id,
            target_shopping_list_id=target.id,
            source_scope_type=payload.preview.source_type,
            source_reference=json.loads(json.dumps(calculated["source"]["reference"], default=str)),
            source_version=calculated["source"]["source_version"],
            pantry_date_mode=payload.preview.pantry_date_mode,
            other_open_lists_considered=payload.preview.include_other_open_lists,
            client_operation_id=payload.client_operation_id,
            result_summary=calculated["summary"],
        )
        session.add(operation)
        session.flush()
        created = updated = preserved = 0
        position = max((item.position for item in target.items), default=-1) + 1
        reset_ids = set(payload.preview.reset_override_item_ids)
        for row in calculated["items"]:
            matches = [item for item in target.items if item.food_id == row["food_id"]]
            resolution = payload.preview.target_item_resolutions.get(str(row["food_id"]))
            generated = [item for item in matches if item.origin_type == "generated"]
            item = generated[0] if len(generated) == 1 else None
            if resolution != "create_separate" and resolution is not None:
                item = next(
                    (candidate for candidate in matches if candidate.id == resolution), None
                )
                if item is None:
                    raise _error(
                        "PANTRY_AWARE_TARGET_ITEM_CONFLICT",
                        "Die gewählte Zielposition ist nicht mehr verfügbar.",
                        409,
                    )
            if item is None and matches and resolution is None:
                raise _error(
                    "PANTRY_AWARE_MANUAL_ITEM_CONFIRMATION_REQUIRED"
                    if len(matches) == 1
                    else "PANTRY_AWARE_TARGET_ITEM_CONFLICT",
                    "Bitte entscheide, wie der bestehende Eintrag behandelt werden soll.",
                    409,
                )
            if item is None:
                item = ShoppingListItem(
                    shopping_list=target,
                    item_type="food",
                    origin_type="generated",
                    food_id=row["food_id"],
                    food_name_snapshot=row["food_name"],
                    category_code=row["category_code"],
                    position=position,
                    canonical_unit=row["canonical_unit"],
                    purchase_unit_code=row["canonical_unit"],
                    purchase_quantity=row["desired_target_commitment"],
                )
                position += 1
                session.add(item)
                session.flush()
                created += 1
            else:
                updated += 1
            item.required_quantity = row["combined_requirement"]
            item.pantry_available_quantity = row["pantry_available"]
            item.suggested_purchase_quantity = row["desired_target_commitment"]
            if item.quantity_overridden and item.id not in reset_ids:
                preserved += 1
            else:
                item.purchase_quantity = row["desired_target_commitment"]
                item.purchase_unit_code = row["canonical_unit"]
                item.quantity_overridden = False
            known = {source.source_identity for source in item.sources}
            for source in row["source_contributions"]:
                if source["source_identity"] in known:
                    continue
                session.add(
                    ShoppingListItemSource(
                        shopping_list_item_id=item.id,
                        source_type=source["source_type"],
                        source_identity=source["source_identity"],
                        source_version=calculated["source"]["source_version"],
                        pantry_aware_operation_id=operation.id,
                        daily_plan_id=source["daily_plan_id"],
                        plan_date=source["plan_date"],
                        meal_id=source["meal_id"],
                        meal_name_snapshot=source["meal_name"],
                        meal_entry_id=source["meal_entry_id"],
                        recipe_id=source["recipe_id"],
                        recipe_name_snapshot=source["recipe_name"],
                        recipe_ingredient_id=source["recipe_ingredient_id"],
                        food_id=row["food_id"],
                        quantity=source["quantity"],
                        unit=source["unit"],
                        conversion_estimated=source["conversion_estimated"],
                        refreshed_at=utc_now(),
                    )
                )
        target.source_type = "mixed"
        target.pantry_considered = True
        target.version += 1
        operation.result_summary = {
            **calculated["summary"],
            "created_item_count": created,
            "updated_item_count": updated,
            "preserved_override_count": preserved,
        }
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "operation_id": operation.id,
        "target_shopping_list_id": target.id,
        "summary": operation.result_summary,
        "idempotent_replay": False,
    }
