# mypy: disable-error-code="type-arg"
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.core.errors import ApiError
from app.database.session import get_db

from . import service
from .models import EnergyCalibrationRecord
from .schemas import ApplyRequest, DeclineRequest, PreviewRequest

router = APIRouter(prefix="/api/v1/energy-calibration", tags=["energy-calibration"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/eligibility")
def eligibility(profile_id: CurrentProfileId, session: Db) -> dict:
    return service.eligibility(session, profile_id)


@router.get("/eligible-windows")
def windows(profile_id: CurrentProfileId, session: Db) -> dict:
    return service.eligible_windows(session, profile_id)


@router.post("/preview")
def preview(payload: PreviewRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.preview(session, profile_id, payload)


def _verified(session: Session, owner: UUID, token: str, request: PreviewRequest) -> dict:
    current = service.preview(session, owner, request)
    if current["preview_token"] != token:
        raise ApiError(
            "ENERGY_CALIBRATION_PREVIEW_STALE",
            "Die Datengrundlage hat sich geändert. Bitte erstelle eine neue Vorschau.",
            409,
        )
    return current


@router.post("/apply")
def apply(payload: ApplyRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    duplicate = session.scalar(
        select(EnergyCalibrationRecord).where(
            EnergyCalibrationRecord.owner_profile_id == profile_id,
            EnergyCalibrationRecord.client_operation_id == payload.client_operation_id,
        )
    )
    if duplicate:
        return service.serialize(duplicate)
    current = _verified(session, profile_id, payload.preview_token, payload.preview)
    proposal = current["proposal"]
    if not isinstance(proposal, dict) or not proposal.get("available"):
        raise ApiError(
            "ENERGY_CALIBRATION_NOT_APPLICABLE",
            "Für diese Datengrundlage wird keine Anpassung vorgeschlagen.",
            409,
        )
    proposed = Decimal(str(proposal["proposed_adjustment_kcal_per_day"]))
    accepted = (
        payload.accepted_adjustment_kcal_per_day
        if payload.accepted_adjustment_kcal_per_day is not None
        else proposed
    )
    if accepted != proposed:
        raise ApiError(
            "ENERGY_CALIBRATION_ADJUSTMENT_CHANGED",
            "Die bestätigte Anpassung stimmt nicht mehr mit der Vorschau überein.",
            409,
        )
    for old in session.scalars(
        select(EnergyCalibrationRecord).where(
            EnergyCalibrationRecord.owner_profile_id == profile_id,
            EnergyCalibrationRecord.status == "accepted",
        )
    ):
        old.status = "superseded"
    record = service.persist(
        session,
        profile_id,
        payload.client_operation_id,
        current,
        status="accepted",
        accepted=accepted,
    )
    revision = service.create_revision(session, profile_id, record, accepted)
    session.commit()
    session.refresh(record)
    result = service.serialize(record)
    result["created_assessment_id"] = str(revision.id)
    return result


@router.post("/decline")
def decline(payload: DeclineRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    current = _verified(session, profile_id, payload.preview_token, payload.preview)
    record = service.persist(
        session, profile_id, payload.client_operation_id, current, status="declined"
    )
    session.commit()
    session.refresh(record)
    return service.serialize(record)


@router.get("/history")
def history(profile_id: CurrentProfileId, session: Db) -> dict:
    return {"items": service.history(session, profile_id)}


@router.get("/{record_id}")
def detail(record_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    record = session.scalar(
        select(EnergyCalibrationRecord).where(
            EnergyCalibrationRecord.id == record_id,
            EnergyCalibrationRecord.owner_profile_id == profile_id,
        )
    )
    if record is None:
        raise ApiError(
            "ENERGY_CALIBRATION_NOT_FOUND", "Die Kalibrierung wurde nicht gefunden.", 404
        )
    return service.serialize(record)
