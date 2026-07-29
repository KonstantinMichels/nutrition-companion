# mypy: disable-error-code="type-arg"

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.pantry import service
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

router = APIRouter(prefix="/api/v1/pantry", tags=["pantry"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/summary")
def pantry_summary(profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.summary(session, profile_id)


@router.get("/locations")
def list_locations(
    profile_id: CurrentProfileId, session: DbSession, include_archived: bool = False
) -> list[dict]:
    return service.locations(session, profile_id, include_archived)


@router.post("/locations", status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationWrite, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.create_location(session, profile_id, payload)


@router.get("/locations/{location_id}")
def location_detail(location_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service._location_dict(service._location(session, profile_id, location_id))


@router.patch("/locations/{location_id}")
def update_location(
    location_id: UUID, payload: LocationPatch, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.update_location(session, profile_id, location_id, payload)


@router.delete("/locations/{location_id}")
def archive_location(location_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.archive_location(session, profile_id, location_id)


@router.post("/locations/{location_id}/restore")
def restore_location(location_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.restore_location(session, profile_id, location_id)


@router.get("/items")
def list_items(
    profile_id: CurrentProfileId,
    session: DbSession,
    query: str | None = None,
    location_id: UUID | None = None,
    category: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    include_depleted: bool = False,
    include_archived: bool = False,
    sort: str = "food_name",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    return service.list_stock(
        session,
        profile_id,
        query=query,
        location_id=location_id,
        category=category,
        status=status_filter,
        include_depleted=include_depleted,
        include_archived=include_archived,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/availability")
def availability(
    profile_id: CurrentProfileId,
    session: DbSession,
    food_id: UUID | None = None,
    location_id: UUID | None = None,
) -> list[dict]:
    return service.availability(session, profile_id, food_id, location_id)


@router.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(payload: StockCreate, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.create_stock(session, profile_id, payload)


@router.get("/items/{lot_id}")
def item_detail(lot_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.detail(session, profile_id, lot_id)


@router.patch("/items/{lot_id}")
def update_item(
    lot_id: UUID, payload: StockPatch, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.update_stock(session, profile_id, lot_id, payload)


@router.get("/items/{lot_id}/movements")
def movement_history(
    lot_id: UUID,
    profile_id: CurrentProfileId,
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    return service.movements(session, profile_id, lot_id, page, page_size)


@router.post("/items/{lot_id}/add")
def add_stock(
    lot_id: UUID, payload: QuantityOperation, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.operate(session, profile_id, lot_id, payload, "add_stock")


@router.post("/items/{lot_id}/consume")
def consume(
    lot_id: UUID, payload: QuantityOperation, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.operate(session, profile_id, lot_id, payload, "consume")


@router.post("/items/{lot_id}/discard")
def discard(
    lot_id: UUID, payload: QuantityOperation, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.operate(session, profile_id, lot_id, payload, "discard")


@router.post("/items/{lot_id}/correct")
def correct(
    lot_id: UUID, payload: CorrectionOperation, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.correct(session, profile_id, lot_id, payload)


@router.post("/items/{lot_id}/transfer")
def transfer(
    lot_id: UUID, payload: TransferOperation, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.transfer(session, profile_id, lot_id, payload)


@router.delete("/items/{lot_id}")
def archive_item(
    lot_id: UUID,
    profile_id: CurrentProfileId,
    session: DbSession,
    payload: ArchiveRequest = Body(default=ArchiveRequest()),
) -> dict:
    return service.archive_stock(session, profile_id, lot_id, payload)


@router.post("/items/{lot_id}/restore")
def restore_item(lot_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.restore_stock(session, profile_id, lot_id)
