from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.modules.foods import repository as food_repository
from app.modules.pantry import service as pantry_service
from app.modules.pantry.models import PantryMovement
from app.modules.pantry.schemas import QuantityOperation, StockCreate
from app.modules.purchase_to_pantry.models import (
    PurchaseToPantryDestination,
    PurchaseToPantryHandoff,
    PurchaseToPantryHandoffItem,
)
from app.modules.purchase_to_pantry.schemas import ApplyRequest, PreviewRequest
from app.modules.shopping_lists.models import ShoppingList, ShoppingListItem


def _error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


LOAD = (selectinload(ShoppingList.items).selectinload(ShoppingListItem.food),)


def _list(
    session: Session,
    profile_id: UUID,
    list_id: UUID,
    *,
    lock: bool = False,
    allow_archived: bool = False,
) -> ShoppingList:
    stmt = (
        select(ShoppingList)
        .where(ShoppingList.id == list_id, ShoppingList.owner_profile_id == profile_id)
        .options(*LOAD)
    )
    if lock:
        stmt = stmt.with_for_update()
    value = session.scalar(stmt)
    if value is None:
        raise _error(
            "PURCHASE_HANDOFF_LIST_NOT_FOUND", "Die Einkaufsliste wurde nicht gefunden.", 404
        )
    if value.is_archived and not allow_archived:
        raise _error(
            "PURCHASE_HANDOFF_LIST_ARCHIVED",
            "Archivierte Einkaufslisten müssen zuerst wiederhergestellt werden.",
            409,
        )
    if not value.items:
        raise _error(
            "PURCHASE_HANDOFF_LIST_EMPTY", "Die Einkaufsliste enthält keine Einträge.", 409
        )
    return value


def eligibility(session: Session, profile_id: UUID, list_id: UUID) -> dict[str, Any]:
    shopping = _list(session, profile_id, list_id)
    rows = []
    for item in shopping.items:
        planned = item.purchase_quantity if item.item_type == "food" else item.manual_quantity
        unit = item.purchase_unit_code if item.item_type == "food" else item.manual_unit_label
        rows.append(
            {
                "shopping_list_item_id": item.id,
                "name": item.food_name_snapshot or item.manual_name,
                "item_type": item.item_type,
                "food_id": item.food_id,
                "checked": item.is_checked,
                "preselected": item.is_checked
                and item.pantry_handoff_state != "completed"
                and item.food_id is not None,
                "planned_purchase_quantity": planned,
                "planned_purchase_unit": unit,
                "handoff_state": item.pantry_handoff_state,
                "previously_transferred_quantity": item.pantry_transferred_quantity,
                "requires_food_mapping": item.food_id is None,
                "eligible": item.food_id is not None,
            }
        )
    return {
        "shopping_list": {"id": shopping.id, "name": shopping.name, "status": shopping.status},
        "items": rows,
    }


def _calculate(
    session: Session,
    profile_id: UUID,
    list_id: UUID,
    payload: PreviewRequest,
    *,
    lock: bool = False,
) -> tuple[ShoppingList, list[dict[str, Any]], str]:
    shopping = _list(session, profile_id, list_id, lock=lock)
    by_id = {item.id: item for item in shopping.items}
    if len({i.shopping_list_item_id for i in payload.items}) != len(payload.items):
        raise _error("PURCHASE_HANDOFF_DUPLICATE_ITEM", "Ein Eintrag wurde mehrfach ausgewählt.")
    calculated: list[dict[str, Any]] = []
    token_parts: list[Any] = [str(shopping.id), shopping.version]
    for request_item in payload.items:
        item = by_id.get(request_item.shopping_list_item_id)
        if item is None:
            raise _error(
                "PURCHASE_HANDOFF_ITEM_NOT_FOUND",
                "Ein ausgewählter Eintrag wurde nicht gefunden.",
                404,
            )
        food_id = item.food_id or request_item.mapped_food_id
        if food_id is None:
            raise _error(
                "PURCHASE_HANDOFF_FOOD_MAPPING_REQUIRED",
                "Ein Freitext-Eintrag muss einem Lebensmittel zugeordnet werden.",
            )
        food = food_repository.get_food(session, profile_id, food_id)
        if food is None:
            raise _error(
                "PURCHASE_HANDOFF_FOOD_NOT_FOUND",
                "Das zugeordnete Lebensmittel wurde nicht gefunden.",
                404,
            )
        if food.is_archived:
            raise _error(
                "PURCHASE_HANDOFF_FOOD_ARCHIVED",
                "Das Lebensmittel muss vor der Übernahme wiederhergestellt werden.",
                409,
            )
        actual, canonical_unit, actual_estimated = pantry_service.normalize(
            food, request_item.actual_quantity, request_item.unit_code, request_item.food_measure_id
        )
        if (
            item.pantry_handoff_state == "completed"
            and not request_item.confirm_additional_after_completion
        ):
            raise _error(
                "PURCHASE_HANDOFF_ALREADY_COMPLETED",
                "Bestätige ausdrücklich, dass weiterer Bestand hinzugefügt werden soll.",
                409,
            )
        destinations = []
        destination_total = Decimal(0)
        for index, destination in enumerate(request_item.destinations):
            normalized, unit, estimated = pantry_service.normalize(
                food, destination.quantity, destination.unit_code, destination.food_measure_id
            )
            if unit != canonical_unit:
                raise _error(
                    "PURCHASE_HANDOFF_UNIT_MISMATCH",
                    "Die Zielmengen verwenden inkompatible Einheiten.",
                )
            location = pantry_service._location(session, profile_id, destination.pantry_location_id)
            if location.is_archived:
                raise _error(
                    "PURCHASE_HANDOFF_LOCATION_ARCHIVED",
                    "Ein ausgewählter Lagerort ist archiviert.",
                    409,
                )
            lot = None
            if destination.destination_type == "existing_stock_lot":
                assert destination.target_stock_lot_id is not None
                lot = pantry_service._lot(
                    session, profile_id, destination.target_stock_lot_id, lock=lock
                )
                if (
                    lot.food_id != food.id
                    or lot.location_id != destination.pantry_location_id
                    or lot.is_archived
                    or lot.is_depleted
                    or lot.location.is_archived
                ):
                    raise _error(
                        "PURCHASE_HANDOFF_LOT_INCOMPATIBLE",
                        "Der bestehende Bestand ist nicht kompatibel.",
                        409,
                    )
                if (
                    destination.expected_lot_version is not None
                    and lot.version != destination.expected_lot_version
                ):
                    raise _error(
                        "PURCHASE_HANDOFF_PREVIEW_STALE",
                        "Der Bestand wurde seit der Vorschau geändert.",
                        409,
                    )
                has_dates = any(
                    (
                        destination.purchase_date,
                        destination.opened_date,
                        destination.best_before_date,
                        destination.use_by_date,
                    )
                )
                exact = (
                    destination.purchase_date,
                    destination.opened_date,
                    destination.best_before_date,
                    destination.use_by_date,
                ) == (lot.purchase_date, lot.opened_date, lot.best_before_date, lot.use_by_date)
                if has_dates and not exact and not destination.confirm_same_lot_metadata:
                    raise _error(
                        "PURCHASE_HANDOFF_LOT_METADATA_CONFLICT",
                        "Abweichende Datumsangaben erfordern einen neuen Bestand.",
                        409,
                    )
            destination_total += normalized
            destinations.append(
                {
                    "index": index,
                    "input": destination,
                    "normalized_quantity": normalized,
                    "normalized_unit": unit,
                    "conversion_estimated": estimated,
                    "location_name": location.name,
                    "lot": lot,
                }
            )
            token_parts.append(
                [
                    str(item.id),
                    index,
                    str(normalized),
                    str(lot.id) if lot else None,
                    lot.version if lot else None,
                    str(location.id),
                    destination.model_dump(mode="json"),
                ]
            )
        if destination_total != actual:
            raise _error(
                "PURCHASE_HANDOFF_DESTINATION_SUM_MISMATCH",
                "Die Zielmengen müssen exakt der tatsächlich gekauften Menge entsprechen.",
            )
        planned = item.purchase_quantity if item.item_type == "food" else item.manual_quantity
        calculated.append(
            {
                "item": item,
                "food": food,
                "actual": actual,
                "canonical_unit": canonical_unit,
                "actual_estimated": actual_estimated,
                "planned": planned,
                "planned_unit": item.purchase_unit_code
                if item.item_type == "food"
                else item.manual_unit_label,
                "previous_transferred": item.pantry_transferred_quantity,
                "difference": None
                if planned is None or item.canonical_unit not in {None, canonical_unit}
                else actual - planned,
                "destinations": destinations,
                "request": request_item,
            }
        )
    token = hashlib.sha256(
        json.dumps(token_parts, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()
    return shopping, calculated, token


def preview(
    session: Session, profile_id: UUID, list_id: UUID, payload: PreviewRequest
) -> dict[str, Any]:
    shopping, items, token = _calculate(session, profile_id, list_id, payload)
    return _result(shopping, items, token)


def _result(
    shopping: ShoppingList,
    items: list[dict[str, Any]],
    token: str | None,
    handoff_id: UUID | None = None,
) -> dict[str, Any]:
    rows = []
    for row in items:
        item, request = row["item"], row["request"]
        rows.append(
            {
                "shopping_list_item_id": item.id,
                "food_id": row["food"].id,
                "name": item.food_name_snapshot or item.manual_name,
                "planned_purchase_quantity": row["planned"],
                "actual_transferred_quantity": row["actual"],
                "canonical_unit": row["canonical_unit"],
                "difference": row["difference"],
                "previously_transferred_quantity": row["previous_transferred"],
                "resulting_total_transferred_quantity": row["previous_transferred"] + row["actual"],
                "resulting_handoff_state": "completed"
                if request.mark_item_handoff_completed
                else "partial",
                "destinations": [
                    {
                        "destination_type": d["input"].destination_type,
                        "location_name": d["location_name"],
                        "normalized_quantity": d["normalized_quantity"],
                        "normalized_unit": d["normalized_unit"],
                        "purchase_date": d["input"].purchase_date,
                        "best_before_date": d["input"].best_before_date,
                        "use_by_date": d["input"].use_by_date,
                        "conversion_estimated": d["conversion_estimated"],
                    }
                    for d in row["destinations"]
                ],
                "warnings": [],
            }
        )
    return {
        "handoff_id": handoff_id,
        "shopping_list": {"id": shopping.id, "name": shopping.name, "status": shopping.status},
        "items": rows,
        "summary": {
            "selected_item_count": len(rows),
            "new_stock_lot_count": sum(
                d["input"].destination_type == "new_stock_lot"
                for r in items
                for d in r["destinations"]
            ),
            "existing_stock_lot_update_count": sum(
                d["input"].destination_type == "existing_stock_lot"
                for r in items
                for d in r["destinations"]
            ),
            "estimated_conversion_count": sum(
                d["conversion_estimated"] for r in items for d in r["destinations"]
            ),
        },
        "warnings": [],
        "preview_token": token,
    }


def apply(
    session: Session, profile_id: UUID, list_id: UUID, payload: ApplyRequest
) -> dict[str, Any]:
    existing = session.scalar(
        select(PurchaseToPantryHandoff)
        .where(
            PurchaseToPantryHandoff.owner_profile_id == profile_id,
            PurchaseToPantryHandoff.client_operation_id == payload.client_operation_id,
        )
        .options(
            selectinload(PurchaseToPantryHandoff.items).selectinload(
                PurchaseToPantryHandoffItem.destinations
            )
        )
    )
    if existing:
        return handoff_detail(session, profile_id, list_id, existing.id)
    shopping, items, token = _calculate(session, profile_id, list_id, payload, lock=True)
    if token != payload.preview_token:
        raise _error("PURCHASE_HANDOFF_PREVIEW_STALE", "Die Vorschau ist nicht mehr aktuell.", 409)
    handoff = PurchaseToPantryHandoff(
        owner_profile_id=profile_id,
        shopping_list_id=shopping.id,
        shopping_list_name_snapshot=shopping.name,
        client_operation_id=payload.client_operation_id,
        status="completed",
        completed_at=datetime.now(UTC),
    )
    session.add(handoff)
    session.flush()
    try:
        for row in items:
            item, request = row["item"], row["request"]
            hi = PurchaseToPantryHandoffItem(
                handoff=handoff,
                shopping_list_item_id=item.id,
                food_id=row["food"].id,
                shopping_item_name_snapshot=item.food_name_snapshot
                or item.manual_name
                or "Lebensmittel",
                planned_purchase_quantity=row["planned"],
                planned_purchase_unit=row["planned_unit"],
                actual_transferred_quantity=row["actual"],
                canonical_unit=row["canonical_unit"],
                mark_item_handoff_completed=request.mark_item_handoff_completed,
            )
            session.add(hi)
            session.flush()
            for d in row["destinations"]:
                value = d["input"]
                operation_id = uuid5(payload.client_operation_id, f"{item.id}:{d['index']}")
                if value.destination_type == "new_stock_lot":
                    result = pantry_service.create_stock(
                        session,
                        profile_id,
                        StockCreate(
                            client_operation_id=operation_id,
                            food_id=row["food"].id,
                            location_id=value.pantry_location_id,
                            quantity=value.quantity,
                            unit_code=value.unit_code,
                            food_measure_id=value.food_measure_id,
                            purchase_date=value.purchase_date,
                            opened_date=value.opened_date,
                            best_before_date=value.best_before_date,
                            use_by_date=value.use_by_date,
                            note=value.note,
                        ),
                        commit=False,
                        source_type="shopping_list_purchase",
                    )
                else:
                    assert value.target_stock_lot_id is not None
                    result = pantry_service.operate(
                        session,
                        profile_id,
                        value.target_stock_lot_id,
                        QuantityOperation(
                            client_operation_id=operation_id,
                            quantity=value.quantity,
                            unit_code=value.unit_code,
                            food_measure_id=value.food_measure_id,
                            note=value.note,
                        ),
                        "add_stock",
                        commit=False,
                        source_type="shopping_list_purchase",
                    )
                lot_id = UUID(str(result["id"]))
                movement = session.scalar(
                    select(PantryMovement).where(
                        PantryMovement.owner_profile_id == profile_id,
                        PantryMovement.client_operation_id == operation_id,
                    )
                )
                assert movement is not None
                session.add(
                    PurchaseToPantryDestination(
                        handoff_item=hi,
                        destination_type=value.destination_type,
                        pantry_location_id=value.pantry_location_id,
                        target_stock_lot_id=value.target_stock_lot_id,
                        created_stock_lot_id=lot_id
                        if value.destination_type == "new_stock_lot"
                        else None,
                        pantry_movement_id=movement.id,
                        entered_quantity=value.quantity,
                        entered_unit_code=value.unit_code,
                        food_measure_id=value.food_measure_id,
                        normalized_quantity=d["normalized_quantity"],
                        normalized_unit=d["normalized_unit"],
                        conversion_estimated=d["conversion_estimated"],
                        purchase_date=value.purchase_date,
                        opened_date=value.opened_date,
                        best_before_date=value.best_before_date,
                        use_by_date=value.use_by_date,
                        note=value.note,
                    )
                )
            item.pantry_transferred_quantity += row["actual"]
            item.pantry_handoff_state = (
                "completed" if request.mark_item_handoff_completed else "partial"
            )
        shopping.version += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _result(shopping, items, None, handoff.id)


HISTORY_LOAD = (
    selectinload(PurchaseToPantryHandoff.items)
    .selectinload(PurchaseToPantryHandoffItem.destinations)
    .selectinload(PurchaseToPantryDestination.location),
)


def history(
    session: Session, profile_id: UUID, list_id: UUID, item_id: UUID | None = None
) -> list[dict[str, Any]]:
    _list(session, profile_id, list_id, allow_archived=True)
    stmt = (
        select(PurchaseToPantryHandoff)
        .where(
            PurchaseToPantryHandoff.owner_profile_id == profile_id,
            PurchaseToPantryHandoff.shopping_list_id == list_id,
        )
        .options(*HISTORY_LOAD)
        .order_by(PurchaseToPantryHandoff.created_at.desc())
    )
    rows = list(session.scalars(stmt).unique())
    result = []
    for h in rows:
        selected = [i for i in h.items if item_id is None or i.shopping_list_item_id == item_id]
        if selected:
            result.append(_history_dict(h, selected))
    return result


def _history_dict(
    h: PurchaseToPantryHandoff, items: list[PurchaseToPantryHandoffItem] | None = None
) -> dict[str, Any]:
    return {
        "id": h.id,
        "shopping_list_id": h.shopping_list_id,
        "shopping_list_name": h.shopping_list_name_snapshot,
        "status": h.status,
        "completed_at": h.completed_at,
        "items": [
            {
                "shopping_list_item_id": i.shopping_list_item_id,
                "name": i.shopping_item_name_snapshot,
                "food_id": i.food_id,
                "actual_transferred_quantity": i.actual_transferred_quantity,
                "canonical_unit": i.canonical_unit,
                "mark_item_handoff_completed": i.mark_item_handoff_completed,
                "destinations": [
                    {
                        "destination_type": d.destination_type,
                        "pantry_location_id": d.pantry_location_id,
                        "location_name": d.location.name,
                        "stock_lot_id": d.created_stock_lot_id or d.target_stock_lot_id,
                        "pantry_movement_id": d.pantry_movement_id,
                        "normalized_quantity": d.normalized_quantity,
                        "normalized_unit": d.normalized_unit,
                    }
                    for d in i.destinations
                ],
            }
            for i in (items or h.items)
        ],
    }


def handoff_detail(
    session: Session, profile_id: UUID, list_id: UUID, handoff_id: UUID
) -> dict[str, Any]:
    _list(session, profile_id, list_id, allow_archived=True)
    h = session.scalar(
        select(PurchaseToPantryHandoff)
        .where(
            PurchaseToPantryHandoff.id == handoff_id,
            PurchaseToPantryHandoff.owner_profile_id == profile_id,
            PurchaseToPantryHandoff.shopping_list_id == list_id,
        )
        .options(*HISTORY_LOAD)
    )
    if h is None:
        raise _error("PURCHASE_HANDOFF_NOT_FOUND", "Die Übernahme wurde nicht gefunden.", 404)
    return _history_dict(h)
