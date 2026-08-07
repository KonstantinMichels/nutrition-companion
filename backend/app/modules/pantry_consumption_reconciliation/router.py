# ruff: noqa: E501
# mypy: disable-error-code="type-arg"
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db

from . import service
from .schemas import (
    ApplyRequest,
    DayDeletionResolution,
    EntryDeletionResolution,
    PreviewRequest,
    ReversalApplyRequest,
    ReversalPreviewRequest,
)

router = APIRouter(prefix="/api/v1", tags=["pantry-consumption-reconciliation"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/consumption-days/{day_id}/pantry-reconciliation")
def day_status(day_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.status_for_day(db, profile_id, day_id)


@router.get("/consumption-entries/{entry_id}/pantry-reconciliation")
def entry_status(entry_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.status_for_entry(db, profile_id, entry_id)


@router.post("/consumption-days/{day_id}/pantry-reconciliation/preview")
def preview(day_id: UUID, payload: PreviewRequest, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.preview(db, profile_id, day_id, payload)


@router.post("/consumption-days/{day_id}/pantry-reconciliation/apply")
def apply(day_id: UUID, payload: ApplyRequest, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.apply(db, profile_id, day_id, payload)


@router.get("/pantry-consumption-reconciliations")
def history(
    profile_id: CurrentProfileId,
    db: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    consumption_day_id: UUID | None = None,
    consumption_entry_id: UUID | None = None,
    food_id: UUID | None = None,
    pantry_stock_lot_id: UUID | None = None,
    status: str | None = None,
    has_reversal: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    sort: str = "applied_at_desc",
) -> dict:
    # Additional filters remain accepted for a stable API; lightweight history never loads nutrients.
    return service.history(
        db,
        profile_id,
        day_id=consumption_day_id,
        entry_id=consumption_entry_id,
        food_id=food_id,
        lot_id=pantry_stock_lot_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        has_reversal=has_reversal,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/pantry-consumption-reconciliations/{batch_id}")
def detail(batch_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.detail(db, profile_id, batch_id)


@router.post("/pantry-consumption-reconciliations/{batch_id}/reversal-preview")
def reversal_preview(
    batch_id: UUID, payload: ReversalPreviewRequest, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.reversal_preview(db, profile_id, batch_id, payload)


@router.post("/pantry-consumption-reconciliations/{batch_id}/reverse")
def reverse(
    batch_id: UUID, payload: ReversalApplyRequest, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.reverse(db, profile_id, batch_id, payload)


@router.get("/consumption-days/{day_id}/pantry-reconciliation/deletion-preview")
def day_deletion_preview(day_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.deletion_preview(db, profile_id, day_id=day_id)


@router.get("/consumption-days/{day_id}/entries/{entry_id}/pantry-reconciliation/deletion-preview")
def entry_deletion_preview(
    day_id: UUID, entry_id: UUID, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.deletion_preview(db, profile_id, day_id=day_id, entry_id=entry_id)


@router.post("/consumption-days/{day_id}/pantry-reconciliation/delete-with-resolution")
def delete_day_with_resolution(
    day_id: UUID, payload: DayDeletionResolution, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.delete_day_with_resolution(db, profile_id, day_id, payload)


@router.post(
    "/consumption-days/{day_id}/entries/{entry_id}/pantry-reconciliation/delete-with-resolution"
)
def delete_entry_with_resolution(
    day_id: UUID,
    entry_id: UUID,
    payload: EntryDeletionResolution,
    profile_id: CurrentProfileId,
    db: Db,
) -> dict:
    return service.delete_entry_with_resolution(db, profile_id, day_id, entry_id, payload)
