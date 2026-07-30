# mypy: disable-error-code="type-arg"
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db

from . import service
from .models import TrainingDayTargetAdjustment
from .schemas import ApplyRequest, PlanLinkRequest, PreferenceWrite, PreviewRequest, SessionWrite

Db = Annotated[Session, Depends(get_db)]
sessions = APIRouter(prefix="/api/v1/training-sessions", tags=["training-day-adjustments"])
adjustments = APIRouter(
    prefix="/api/v1/training-day-adjustments", tags=["training-day-adjustments"]
)
preferences = APIRouter(
    prefix="/api/v1/training-day-adjustment-preferences", tags=["training-day-adjustments"]
)


@sessions.get("")
def session_list(
    profile_id: CurrentProfileId,
    db: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    include_cancelled: bool = False,
) -> list[dict]:
    return service.list_sessions(db, profile_id, date_from, date_to, include_cancelled)


@sessions.post("", status_code=status.HTTP_201_CREATED)
def session_create(payload: SessionWrite, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.save_session(db, profile_id, payload)


@sessions.get("/{item_id}")
def session_detail(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.row(service.require_session(db, profile_id, item_id))


@sessions.patch("/{item_id}")
def session_update(
    item_id: UUID, payload: SessionWrite, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.save_session(db, profile_id, payload, item_id)


@sessions.delete("/{item_id}")
def session_delete(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.delete_session(db, profile_id, item_id)


@sessions.post("/{item_id}/complete")
def session_complete(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.set_session_status(db, profile_id, item_id, "completed")


@sessions.post("/{item_id}/cancel")
def session_cancel(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.set_session_status(db, profile_id, item_id, "cancelled")


@sessions.post("/{item_id}/restore")
def session_restore(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.set_session_status(db, profile_id, item_id, "planned")


@preferences.get("")
def preference_list(
    profile_id: CurrentProfileId, db: Db, include_archived: bool = False
) -> list[dict]:
    return service.list_preferences(db, profile_id, include_archived)


@preferences.post("", status_code=201)
def preference_create(payload: PreferenceWrite, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.save_preference(db, profile_id, payload)


@preferences.get("/{item_id}")
def preference_detail(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.row(service._preference(db, profile_id, item_id))


@preferences.patch("/{item_id}")
def preference_update(
    item_id: UUID, payload: PreferenceWrite, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.save_preference(db, profile_id, payload, item_id)


@preferences.delete("/{item_id}")
def preference_archive(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.archive_preference(db, profile_id, item_id)


@preferences.post("/{item_id}/restore")
def preference_restore(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.archive_preference(db, profile_id, item_id, True)


@adjustments.get("")
def adjustment_list(
    profile_id: CurrentProfileId, db: Db, date_from: date | None = None, date_to: date | None = None
) -> dict:
    return {"items": service.list_adjustments(db, profile_id, date_from, date_to)}


@adjustments.get("/by-date/{day}")
def adjustment_by_date(day: date, profile_id: CurrentProfileId, db: Db) -> dict:
    item = db.scalar(
        select(TrainingDayTargetAdjustment).where(
            TrainingDayTargetAdjustment.owner_profile_id == profile_id,
            TrainingDayTargetAdjustment.adjustment_date == day,
            TrainingDayTargetAdjustment.is_active.is_(True),
        )
    )
    if item is None:
        raise service.error(
            "TRAINING_ADJUSTMENT_NOT_FOUND", "Für diesen Tag besteht keine aktive Anpassung.", 404
        )
    return service.row(item)


@adjustments.post("/preview")
def adjustment_preview(payload: PreviewRequest, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.preview(db, profile_id, payload)


@adjustments.post("/apply")
def adjustment_apply(payload: ApplyRequest, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.apply(db, profile_id, payload)


@adjustments.get("/{item_id}")
def adjustment_detail(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    item = db.scalar(
        select(TrainingDayTargetAdjustment).where(
            TrainingDayTargetAdjustment.id == item_id,
            TrainingDayTargetAdjustment.owner_profile_id == profile_id,
        )
    )
    if item is None:
        raise service.error(
            "TRAINING_ADJUSTMENT_NOT_FOUND", "Die Tagesanpassung wurde nicht gefunden.", 404
        )
    return service.row(item)


@adjustments.post("/{item_id}/cancel")
def adjustment_cancel(item_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.cancel_adjustment(db, profile_id, item_id)


@adjustments.post("/{item_id}/link-daily-plan")
def adjustment_link(
    item_id: UUID, payload: PlanLinkRequest, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.link_plan(
        db, profile_id, item_id, payload.daily_plan_id, payload.create_missing_plan
    )


@adjustments.delete("/daily-plan/{plan_id}/link")
def adjustment_unlink(plan_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.unlink_plan(db, profile_id, plan_id)
