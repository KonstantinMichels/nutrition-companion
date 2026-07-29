from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.modules.foods import repository as food_repository
from app.modules.foods import service as food_service
from app.modules.foods.models import Food
from app.modules.pantry.models import PantryLocation, PantryMovement, PantryStockLot
from app.modules.pantry.schemas import (
    ArchiveRequest,
    CorrectionOperation,
    LocationPatch,
    LocationWrite,
    QuantityOperation,
    StockCreate,
    StockPatch,
    TransferOperation,
)

EXPIRING_SOON_DAYS = 3
DEFAULT_LOCATIONS = (
    ("Vorratsschrank", "pantry"),
    ("Kühlschrank", "refrigerator"),
    ("Gefrierschrank", "freezer"),
)
LOT_LOAD = (
    selectinload(PantryStockLot.food).selectinload(Food.measures),
    selectinload(PantryStockLot.location),
)


def _error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def initialize_locations(session: Session, profile_id: UUID) -> list[PantryLocation]:
    existing = list(
        session.scalars(
            select(PantryLocation)
            .where(PantryLocation.owner_profile_id == profile_id)
            .order_by(PantryLocation.position)
        )
    )
    names = {item.name.casefold() for item in existing if not item.is_archived}
    changed = False
    next_position = len(existing)
    for name, kind in DEFAULT_LOCATIONS:
        if name.casefold() not in names:
            session.add(
                PantryLocation(
                    owner_profile_id=profile_id,
                    name=name,
                    location_type=kind,
                    position=next_position,
                )
            )
            next_position += 1
            changed = True
    if changed:
        session.commit()
    return list(
        session.scalars(
            select(PantryLocation)
            .where(PantryLocation.owner_profile_id == profile_id)
            .order_by(PantryLocation.position)
        )
    )


def locations(
    session: Session, profile_id: UUID, include_archived: bool = False
) -> list[dict[str, Any]]:
    initialize_locations(session, profile_id)
    criteria = [PantryLocation.owner_profile_id == profile_id]
    if not include_archived:
        criteria.append(PantryLocation.is_archived.is_(False))
    items = list(
        session.scalars(
            select(PantryLocation)
            .where(*criteria)
            .options(selectinload(PantryLocation.lots))
            .order_by(PantryLocation.position, PantryLocation.name)
        )
    )
    return [_location_dict(item) for item in items]


def _location(session: Session, profile_id: UUID, location_id: UUID) -> PantryLocation:
    item = session.scalar(
        select(PantryLocation)
        .where(PantryLocation.id == location_id, PantryLocation.owner_profile_id == profile_id)
        .options(selectinload(PantryLocation.lots))
    )
    if item is None:
        raise _error("PANTRY_LOCATION_NOT_FOUND", "Der Lagerort wurde nicht gefunden.", 404)
    return item


def _location_dict(item: PantryLocation) -> dict[str, Any]:
    active = [lot for lot in item.lots if not lot.is_archived and not lot.is_depleted]
    return {
        "id": item.id,
        "name": item.name,
        "location_type": item.location_type,
        "position": item.position,
        "description": item.description,
        "is_archived": item.is_archived,
        "archived_at": item.archived_at,
        "active_lot_count": len(active),
        "active_food_count": len({lot.food_id for lot in active}),
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def create_location(session: Session, profile_id: UUID, payload: LocationWrite) -> dict[str, Any]:
    count = (
        session.scalar(
            select(func.count())
            .select_from(PantryLocation)
            .where(PantryLocation.owner_profile_id == profile_id)
        )
        or 0
    )
    item = PantryLocation(
        owner_profile_id=profile_id,
        name=payload.name,
        location_type=payload.location_type,
        position=payload.position if payload.position is not None else count,
        description=payload.description,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return _location_dict(item)


def update_location(
    session: Session, profile_id: UUID, location_id: UUID, payload: LocationPatch
) -> dict[str, Any]:
    item = _location(session, profile_id, location_id)
    if item.is_archived:
        raise _error(
            "PANTRY_LOCATION_ARCHIVED", "Archivierte Lagerorte sind schreibgeschützt.", 409
        )
    for field in payload.model_fields_set:
        setattr(item, field, getattr(payload, field))
    session.commit()
    return _location_dict(item)


def archive_location(session: Session, profile_id: UUID, location_id: UUID) -> dict[str, Any]:
    item = _location(session, profile_id, location_id)
    active = sum(not lot.is_archived and not lot.is_depleted for lot in item.lots)
    if active:
        raise _error(
            "PANTRY_LOCATION_NOT_EMPTY", f"Der Lagerort enthält noch {active} aktive Bestände.", 409
        )
    item.is_archived = True
    item.archived_at = datetime.now(UTC)
    session.commit()
    return _location_dict(item)


def restore_location(session: Session, profile_id: UUID, location_id: UUID) -> dict[str, Any]:
    item = _location(session, profile_id, location_id)
    item.is_archived = False
    item.archived_at = None
    session.commit()
    return _location_dict(item)


def _food(session: Session, profile_id: UUID, food_id: UUID, *, active: bool = False) -> Food:
    food = food_repository.get_food(session, profile_id, food_id)
    if food is None:
        raise _error("PANTRY_FOOD_NOT_FOUND", "Das Lebensmittel wurde nicht gefunden.", 404)
    if active and food.is_archived:
        raise _error(
            "PANTRY_FOOD_ARCHIVED",
            "Archivierte Lebensmittel können nicht neu eingelagert werden.",
            409,
        )
    return food


def normalize(
    food: Food, quantity: Decimal, unit_code: str, measure_id: UUID | None
) -> tuple[Decimal, str, bool]:
    if quantity <= 0:
        raise _error("PANTRY_INVALID_QUANTITY", "Die Menge muss größer als null sein.")
    if measure_id is not None:
        measure = next((item for item in food.measures if item.id == measure_id), None)
        if measure is None or measure.unit_code != unit_code:
            raise _error(
                "PANTRY_MEASURE_INVALID", "Das Haushaltsmaß gehört nicht zum Lebensmittel."
            )
        direct = measure.equivalent_quantity * quantity / measure.quantity
        try:
            return (
                food_service.normalize_base_quantity(food, direct, measure.equivalent_unit),
                food.reference_unit,
                measure.is_estimated,
            )
        except ApiError as exc:
            raise _error("PANTRY_NORMALIZATION_FAILED", exc.message) from exc
    factor = Decimal(1000) if unit_code in {"kg", "l"} else Decimal(1)
    direct_unit = "g" if unit_code in {"g", "kg"} else "ml" if unit_code in {"ml", "l"} else None
    if direct_unit is None:
        raise _error(
            "PANTRY_UNIT_INCOMPATIBLE", "Für diese Einheit ist ein Haushaltsmaß erforderlich."
        )
    try:
        return (
            food_service.normalize_base_quantity(food, quantity * factor, direct_unit),
            food.reference_unit,
            False,
        )
    except ApiError as exc:
        raise _error(
            "PANTRY_UNIT_INCOMPATIBLE", "Die Einheit ist für dieses Lebensmittel nicht kompatibel."
        ) from exc


def _lot(session: Session, profile_id: UUID, lot_id: UUID, *, lock: bool = False) -> PantryStockLot:
    query = (
        select(PantryStockLot)
        .where(PantryStockLot.id == lot_id, PantryStockLot.owner_profile_id == profile_id)
        .options(*LOT_LOAD)
    )
    if lock:
        query = query.with_for_update()
    item = session.scalar(query)
    if item is None:
        raise _error("PANTRY_ITEM_NOT_FOUND", "Der Vorratsbestand wurde nicht gefunden.", 404)
    return item


def date_status(item: PantryStockLot, anchor: date | None = None) -> str:
    today = anchor or date.today()
    relevant = item.use_by_date or item.best_before_date
    if relevant is None:
        return "no_date"
    if relevant == today:
        return "date_today"
    if relevant < today:
        return "past_use_by" if item.use_by_date else "past_best_before"
    if relevant <= today + timedelta(days=EXPIRING_SOON_DAYS):
        return "expiring_soon"
    return "valid"


def _warnings(item: PantryStockLot) -> list[dict[str, str]]:
    warnings = []
    if item.purchase_date and item.opened_date and item.opened_date < item.purchase_date:
        warnings.append(
            {
                "code": "OPENED_BEFORE_PURCHASE",
                "message_de": "Das Öffnungsdatum liegt vor dem Kaufdatum.",
            }
        )
    relevant_date = item.use_by_date or item.best_before_date
    if item.purchase_date and relevant_date and relevant_date < item.purchase_date:
        warnings.append(
            {
                "code": "DATE_BEFORE_PURCHASE",
                "message_de": "Das relevante Datum liegt vor dem Kaufdatum.",
            }
        )
    if item.use_by_date and item.best_before_date:
        warnings.append(
            {
                "code": "BOTH_DATE_TYPES",
                "message_de": "Mindesthaltbarkeits- und Verbrauchsdatum sind beide hinterlegt.",
            }
        )
    if item.food.is_archived:
        warnings.append(
            {
                "code": "ARCHIVED_FOOD_REFERENCE",
                "message_de": "Das zugehörige Lebensmittel ist archiviert.",
            }
        )
    return warnings


def _movement(
    item: PantryStockLot,
    profile_id: UUID,
    kind: str,
    delta: Decimal,
    before: Decimal,
    after: Decimal,
    operation_id: UUID,
    *,
    entered: Decimal | None = None,
    unit: str | None = None,
    measure_id: UUID | None = None,
    estimated: bool = False,
    note: str | None = None,
    target_location_id: UUID | None = None,
    related_id: UUID | None = None,
) -> PantryMovement:
    return PantryMovement(
        owner_profile_id=profile_id,
        stock_lot=item,
        movement_type=kind,
        quantity_delta=delta,
        normalized_unit=item.normalized_unit,
        balance_before=before,
        balance_after=after,
        entered_quantity=entered,
        entered_unit_code=unit,
        food_measure_id=measure_id,
        conversion_estimated=estimated,
        source_type="manual",
        note=note,
        target_location_id=target_location_id,
        related_stock_lot_id=related_id,
        client_operation_id=operation_id,
    )


def create_stock(session: Session, profile_id: UUID, payload: StockCreate) -> dict[str, Any]:
    existing = _operation_lot(session, profile_id, payload.client_operation_id)
    if existing:
        return detail(session, profile_id, existing)
    food = _food(session, profile_id, payload.food_id, active=True)
    location = _location(session, profile_id, payload.location_id)
    if location.is_archived:
        raise _error("PANTRY_LOCATION_ARCHIVED", "Der Lagerort ist archiviert.", 409)
    normalized, unit, estimated = normalize(
        food, payload.quantity, payload.unit_code, payload.food_measure_id
    )
    lot = PantryStockLot(
        owner_profile_id=profile_id,
        food=food,
        location=location,
        current_quantity=normalized,
        normalized_unit=unit,
        initial_entered_quantity=payload.quantity,
        initial_entered_unit_code=payload.unit_code,
        initial_food_measure_id=payload.food_measure_id,
        initial_conversion_estimated=estimated,
        purchase_date=payload.purchase_date,
        opened_date=payload.opened_date,
        best_before_date=payload.best_before_date,
        use_by_date=payload.use_by_date,
        note=payload.note,
    )
    session.add(lot)
    session.flush()
    session.add(
        _movement(
            lot,
            profile_id,
            "initial_stock",
            normalized,
            Decimal(0),
            normalized,
            payload.client_operation_id,
            entered=payload.quantity,
            unit=payload.unit_code,
            measure_id=payload.food_measure_id,
            estimated=estimated,
            note=payload.note,
        )
    )
    _commit(session)
    return detail(session, profile_id, lot.id)


def _operation_lot(session: Session, profile_id: UUID, operation_id: UUID) -> UUID | None:
    return session.scalar(
        select(PantryMovement.stock_lot_id)
        .where(
            PantryMovement.owner_profile_id == profile_id,
            PantryMovement.client_operation_id == operation_id,
        )
        .limit(1)
    )


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _error(
            "PANTRY_CONCURRENT_MODIFICATION",
            "Der Bestand wurde gleichzeitig geändert. Bitte aktualisiere die Ansicht.",
            409,
        ) from exc


def _lot_dict(
    item: PantryStockLot,
    *,
    movements: list[PantryMovement] | None = None,
    anchor: date | None = None,
) -> dict[str, Any]:
    return {
        "id": item.id,
        "food": {
            "id": item.food.id,
            "name": item.food.name,
            "brand": item.food.brand,
            "is_archived": item.food.is_archived,
            "category_code": item.food.category_code,
        },
        "location": {
            "id": item.location.id,
            "name": item.location.name,
            "location_type": item.location.location_type,
            "is_archived": item.location.is_archived,
        },
        "current_quantity": item.current_quantity,
        "normalized_unit": item.normalized_unit,
        "initial_entered_quantity": item.initial_entered_quantity,
        "initial_entered_unit_code": item.initial_entered_unit_code,
        "initial_food_measure_id": item.initial_food_measure_id,
        "initial_conversion_estimated": item.initial_conversion_estimated,
        "purchase_date": item.purchase_date,
        "opened_date": item.opened_date,
        "best_before_date": item.best_before_date,
        "use_by_date": item.use_by_date,
        "date_status": date_status(item, anchor),
        "note": item.note,
        "is_depleted": item.is_depleted,
        "depleted_at": item.depleted_at,
        "is_archived": item.is_archived,
        "archived_at": item.archived_at,
        "version": item.version,
        "warnings": _warnings(item),
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "movements": [] if movements is None else [_movement_dict(m) for m in movements],
    }


def detail(session: Session, profile_id: UUID, lot_id: UUID) -> dict[str, Any]:
    item = _lot(session, profile_id, lot_id)
    moves = list(
        session.scalars(
            select(PantryMovement)
            .where(
                PantryMovement.owner_profile_id == profile_id, PantryMovement.stock_lot_id == lot_id
            )
            .order_by(PantryMovement.created_at.desc())
            .limit(20)
        )
    )
    return _lot_dict(item, movements=moves)


def update_stock(
    session: Session, profile_id: UUID, lot_id: UUID, payload: StockPatch
) -> dict[str, Any]:
    item = _lot(session, profile_id, lot_id)
    if item.is_archived:
        raise _error("PANTRY_ITEM_ARCHIVED", "Archivierte Bestände sind schreibgeschützt.", 409)
    for field in payload.model_fields_set:
        setattr(item, field, getattr(payload, field))
    session.commit()
    return detail(session, profile_id, item.id)


def operate(
    session: Session, profile_id: UUID, lot_id: UUID, payload: QuantityOperation, kind: str
) -> dict[str, Any]:
    existing = _operation_lot(session, profile_id, payload.client_operation_id)
    if existing:
        return detail(session, profile_id, existing)
    item = _lot(session, profile_id, lot_id, lock=True)
    if item.is_archived:
        raise _error("PANTRY_ITEM_ARCHIVED", "Archivierte Bestände sind schreibgeschützt.", 409)
    if kind == "add_stock" and item.is_depleted and not payload.confirm_depleted_reuse:
        raise _error(
            "PANTRY_ITEM_DEPLETED",
            "Bestätige ausdrücklich, dass der aufgebrauchte Bestand wiederverwendet werden soll.",
            409,
        )
    normalized, _, estimated = normalize(
        item.food, payload.quantity, payload.unit_code, payload.food_measure_id
    )
    before = item.current_quantity
    delta = normalized if kind == "add_stock" else -normalized
    after = before + delta
    if after < 0:
        raise _error(
            "PANTRY_INSUFFICIENT_STOCK",
            "Der verfügbare Bestand reicht für diese Menge nicht aus.",
            409,
        )
    item.current_quantity = after
    item.version += 1
    _depletion(item)
    session.add(
        _movement(
            item,
            profile_id,
            kind,
            delta,
            before,
            after,
            payload.client_operation_id,
            entered=payload.quantity,
            unit=payload.unit_code,
            measure_id=payload.food_measure_id,
            estimated=estimated,
            note=payload.note,
        )
    )
    _commit(session)
    return detail(session, profile_id, item.id)


def correct(
    session: Session, profile_id: UUID, lot_id: UUID, payload: CorrectionOperation
) -> dict[str, Any]:
    existing = _operation_lot(session, profile_id, payload.client_operation_id)
    if existing:
        return detail(session, profile_id, existing)
    item = _lot(session, profile_id, lot_id, lock=True)
    if item.is_archived:
        raise _error("PANTRY_ITEM_ARCHIVED", "Archivierte Bestände sind schreibgeschützt.", 409)
    if payload.new_total_quantity == 0:
        normalized, estimated = Decimal(0), False
    else:
        normalized, _, estimated = normalize(
            item.food, payload.new_total_quantity, payload.unit_code, payload.food_measure_id
        )
    before = item.current_quantity
    delta = normalized - before
    if delta == 0:
        return detail(session, profile_id, item.id)
    item.current_quantity = normalized
    item.version += 1
    _depletion(item)
    kind = "correction_increase" if delta > 0 else "correction_decrease"
    session.add(
        _movement(
            item,
            profile_id,
            kind,
            delta,
            before,
            normalized,
            payload.client_operation_id,
            entered=payload.new_total_quantity,
            unit=payload.unit_code,
            measure_id=payload.food_measure_id,
            estimated=estimated,
            note=payload.note,
        )
    )
    _commit(session)
    return detail(session, profile_id, item.id)


def _depletion(item: PantryStockLot) -> None:
    item.is_depleted = item.current_quantity == 0
    item.depleted_at = datetime.now(UTC) if item.is_depleted else None


def transfer(
    session: Session, profile_id: UUID, lot_id: UUID, payload: TransferOperation
) -> dict[str, Any]:
    existing = _operation_lot(session, profile_id, payload.client_operation_id)
    if existing:
        return detail(session, profile_id, existing)
    source = _lot(session, profile_id, lot_id, lock=True)
    target_location = _location(session, profile_id, payload.target_location_id)
    if source.is_archived:
        raise _error("PANTRY_ITEM_ARCHIVED", "Archivierte Bestände sind schreibgeschützt.", 409)
    if target_location.is_archived:
        raise _error("PANTRY_TARGET_LOCATION_ARCHIVED", "Der Ziellagerort ist archiviert.", 409)
    if source.location_id == target_location.id:
        raise _error(
            "PANTRY_TRANSFER_SAME_LOCATION", "Quelle und Ziel müssen verschieden sein.", 409
        )
    quantity, _, estimated = normalize(
        source.food, payload.quantity, payload.unit_code, payload.food_measure_id
    )
    if quantity > source.current_quantity:
        raise _error(
            "PANTRY_INSUFFICIENT_STOCK",
            "Der verfügbare Bestand reicht für die Umlagerung nicht aus.",
            409,
        )
    before = source.current_quantity
    if quantity == before:
        source.location = target_location
        source.version += 1
        session.add(
            _movement(
                source,
                profile_id,
                "transfer_out",
                Decimal(0),
                before,
                before,
                payload.client_operation_id,
                entered=payload.quantity,
                unit=payload.unit_code,
                measure_id=payload.food_measure_id,
                estimated=estimated,
                note=payload.note,
                target_location_id=target_location.id,
            )
        )
        _commit(session)
        return detail(session, profile_id, source.id)
    source.current_quantity -= quantity
    source.version += 1
    target = PantryStockLot(
        owner_profile_id=profile_id,
        food=source.food,
        location=target_location,
        current_quantity=quantity,
        normalized_unit=source.normalized_unit,
        initial_entered_quantity=payload.quantity,
        initial_entered_unit_code=payload.unit_code,
        initial_food_measure_id=payload.food_measure_id,
        initial_conversion_estimated=estimated,
        purchase_date=source.purchase_date,
        opened_date=source.opened_date,
        best_before_date=source.best_before_date,
        use_by_date=source.use_by_date,
        note=source.note,
    )
    session.add(target)
    session.flush()
    session.add(
        _movement(
            source,
            profile_id,
            "transfer_out",
            -quantity,
            before,
            source.current_quantity,
            payload.client_operation_id,
            entered=payload.quantity,
            unit=payload.unit_code,
            measure_id=payload.food_measure_id,
            estimated=estimated,
            note=payload.note,
            target_location_id=target_location.id,
            related_id=target.id,
        )
    )
    session.add(
        _movement(
            target,
            profile_id,
            "transfer_in",
            quantity,
            Decimal(0),
            quantity,
            payload.client_operation_id,
            entered=payload.quantity,
            unit=payload.unit_code,
            measure_id=payload.food_measure_id,
            estimated=estimated,
            note=payload.note,
            related_id=source.id,
        )
    )
    _commit(session)
    return detail(session, profile_id, target.id)


def archive_stock(
    session: Session, profile_id: UUID, lot_id: UUID, payload: ArchiveRequest
) -> dict[str, Any]:
    item = _lot(session, profile_id, lot_id)
    if not item.is_depleted and item.current_quantity > 0 and not payload.confirm_non_depleted:
        raise _error(
            "PANTRY_ARCHIVE_CONFIRMATION_REQUIRED",
            "Bestätige, dass der vorhandene Bestand aus den verfügbaren Mengen "
            "ausgeschlossen werden soll.",
            409,
        )
    item.is_archived = True
    item.archived_at = datetime.now(UTC)
    session.commit()
    return detail(session, profile_id, item.id)


def restore_stock(session: Session, profile_id: UUID, lot_id: UUID) -> dict[str, Any]:
    item = _lot(session, profile_id, lot_id)
    if item.location.is_archived:
        raise _error("PANTRY_TARGET_LOCATION_ARCHIVED", "Wähle zuerst einen aktiven Lagerort.", 409)
    item.is_archived = False
    item.archived_at = None
    session.add(
        _movement(
            item,
            profile_id,
            "restore",
            Decimal(0),
            item.current_quantity,
            item.current_quantity,
            uuid4(),
        )
    )
    session.commit()
    return detail(session, profile_id, item.id)


def list_stock(
    session: Session,
    profile_id: UUID,
    *,
    query: str | None = None,
    location_id: UUID | None = None,
    category: str | None = None,
    status: str | None = None,
    include_depleted: bool = False,
    include_archived: bool = False,
    sort: str = "food_name",
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    criteria = [PantryStockLot.owner_profile_id == profile_id]
    if not include_depleted:
        criteria.append(PantryStockLot.is_depleted.is_(False))
    if not include_archived:
        criteria.append(PantryStockLot.is_archived.is_(False))
    if location_id:
        criteria.append(PantryStockLot.location_id == location_id)
    if category:
        criteria.append(Food.category_code == category)
    if query:
        pattern = f"%{query.strip().casefold()}%"
        criteria.append(
            or_(
                func.lower(Food.name).like(pattern),
                func.lower(func.coalesce(Food.brand, "")).like(pattern),
                func.lower(func.coalesce(PantryStockLot.note, "")).like(pattern),
            )
        )
    statement = select(PantryStockLot).join(PantryStockLot.food).where(*criteria).options(*LOT_LOAD)
    order = (
        PantryStockLot.current_quantity.asc()
        if sort == "quantity_asc"
        else PantryStockLot.current_quantity.desc()
        if sort == "quantity_desc"
        else PantryStockLot.updated_at.desc()
        if sort == "recent"
        else Food.normalized_name.asc()
    )
    all_items = list(session.scalars(statement.order_by(order)))
    if status:
        all_items = [item for item in all_items if date_status(item) == status]
    total = len(all_items)
    items = all_items[(page - 1) * page_size : page * page_size]
    return {
        "items": [_lot_dict(item) for item in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def availability(
    session: Session, profile_id: UUID, food_id: UUID | None = None, location_id: UUID | None = None
) -> list[dict[str, Any]]:
    criteria = [
        PantryStockLot.owner_profile_id == profile_id,
        PantryStockLot.is_archived.is_(False),
        PantryStockLot.is_depleted.is_(False),
    ]
    if food_id:
        criteria.append(PantryStockLot.food_id == food_id)
    if location_id:
        criteria.append(PantryStockLot.location_id == location_id)
    items = list(session.scalars(select(PantryStockLot).where(*criteria).options(*LOT_LOAD)))
    groups: dict[UUID, list[PantryStockLot]] = {}
    for item in items:
        groups.setdefault(item.food_id, []).append(item)
    result = []
    for fid, lots in groups.items():
        locations: dict[UUID, Decimal] = {}
        for lot in lots:
            locations[lot.location_id] = (
                locations.get(lot.location_id, Decimal(0)) + lot.current_quantity
            )
        result.append(
            {
                "food_id": fid,
                "food_name": lots[0].food.name,
                "brand": lots[0].food.brand,
                "available_quantity": sum((lot.current_quantity for lot in lots), Decimal(0)),
                "unit": lots[0].normalized_unit,
                "active_lot_count": len(lots),
                "locations": [
                    {
                        "location_id": lid,
                        "location_name": next(
                            lot.location.name for lot in lots if lot.location_id == lid
                        ),
                        "quantity": amount,
                        "unit": lots[0].normalized_unit,
                    }
                    for lid, amount in locations.items()
                ],
                "nearest_relevant_date": min(
                    [
                        value
                        for lot in lots
                        if (value := lot.use_by_date or lot.best_before_date) is not None
                    ],
                    default=None,
                ),
                "estimated_conversion_count": sum(lot.initial_conversion_estimated for lot in lots),
                "archived_food": lots[0].food.is_archived,
            }
        )
    return sorted(result, key=lambda item: str(item["food_name"]).casefold())


def summary(session: Session, profile_id: UUID) -> dict[str, int]:
    all_items = list(
        session.scalars(
            select(PantryStockLot)
            .where(PantryStockLot.owner_profile_id == profile_id)
            .options(*LOT_LOAD)
        )
    )
    active = [item for item in all_items if not item.is_archived and not item.is_depleted]
    statuses = [date_status(item) for item in active]
    return {
        "active_food_count": len({item.food_id for item in active}),
        "active_lot_count": len(active),
        "depleted_lot_count": sum(item.is_depleted and not item.is_archived for item in all_items),
        "archived_lot_count": sum(item.is_archived for item in all_items),
        "expiring_soon_count": statuses.count("expiring_soon") + statuses.count("date_today"),
        "past_best_before_count": statuses.count("past_best_before"),
        "past_use_by_count": statuses.count("past_use_by"),
        "location_count": len(locations(session, profile_id)),
        "estimated_conversion_count": sum(item.initial_conversion_estimated for item in active),
    }


def movements(
    session: Session, profile_id: UUID, lot_id: UUID, page: int, page_size: int
) -> dict[str, Any]:
    _lot(session, profile_id, lot_id)
    criteria = [
        PantryMovement.owner_profile_id == profile_id,
        PantryMovement.stock_lot_id == lot_id,
    ]
    total = session.scalar(select(func.count()).select_from(PantryMovement).where(*criteria)) or 0
    items = list(
        session.scalars(
            select(PantryMovement)
            .where(*criteria)
            .order_by(PantryMovement.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return {
        "items": [_movement_dict(item) for item in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def _movement_dict(item: PantryMovement) -> dict[str, Any]:
    return {
        "id": item.id,
        "movement_type": item.movement_type,
        "quantity_delta": item.quantity_delta,
        "normalized_unit": item.normalized_unit,
        "balance_before": item.balance_before,
        "balance_after": item.balance_after,
        "entered_quantity": item.entered_quantity,
        "entered_unit_code": item.entered_unit_code,
        "food_measure_id": item.food_measure_id,
        "conversion_estimated": item.conversion_estimated,
        "source_type": item.source_type,
        "note": item.note,
        "target_location_id": item.target_location_id,
        "related_stock_lot_id": item.related_stock_lot_id,
        "client_operation_id": item.client_operation_id,
        "created_at": item.created_at,
    }
