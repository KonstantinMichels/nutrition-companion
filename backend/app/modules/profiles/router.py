from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.core.errors import ApiError
from app.database.session import get_db
from app.modules.profiles import repository, service
from app.modules.profiles.schemas import (
    ActivityResponse,
    ActivityUpdate,
    GoalResponse,
    GoalUpdate,
    HealthScreeningResponse,
    HealthScreeningUpdate,
    ProfileResponse,
    ProfileUpdate,
    RestrictionsResponse,
    RestrictionsUpdate,
)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ProfileResponse)
def read_profile(profile_id: CurrentProfileId, session: DbSession) -> object:
    return service.require_profile(session, profile_id)


@router.put("", response_model=ProfileResponse)
def put_profile(payload: ProfileUpdate, profile_id: CurrentProfileId, session: DbSession) -> object:
    return service.update_profile(session, profile_id, payload)


@router.get("/activity", response_model=ActivityResponse)
def read_activity(profile_id: CurrentProfileId, session: DbSession) -> object:
    activity = repository.get_activity(session, profile_id)
    if activity is None:
        raise ApiError(
            code="ACTIVITY_NOT_FOUND",
            message="Es wurden noch keine Aktivitätsdaten gespeichert.",
            status_code=404,
        )
    return activity


@router.put("/activity", response_model=ActivityResponse)
def put_activity(
    payload: ActivityUpdate, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return service.update_activity(session, profile_id, payload)


@router.get("/goal", response_model=GoalResponse)
def read_goal(profile_id: CurrentProfileId, session: DbSession) -> object:
    goal = repository.get_goal(session, profile_id)
    if goal is None:
        raise ApiError(
            code="GOAL_NOT_FOUND",
            message="Es wurde noch kein Ernährungsziel gespeichert.",
            status_code=404,
        )
    return goal


@router.put("/goal", response_model=GoalResponse)
def put_goal(payload: GoalUpdate, profile_id: CurrentProfileId, session: DbSession) -> object:
    return service.update_goal(session, profile_id, payload)


@router.get("/restrictions", response_model=RestrictionsResponse)
def read_restrictions(profile_id: CurrentProfileId, session: DbSession) -> object:
    service.require_profile(session, profile_id)
    return {"restrictions": repository.get_restrictions(session, profile_id)}


@router.put("/restrictions", response_model=RestrictionsResponse)
def put_restrictions(
    payload: RestrictionsUpdate, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return {"restrictions": service.update_restrictions(session, profile_id, payload)}


@router.get("/health-screening", response_model=HealthScreeningResponse)
def read_health_screening(profile_id: CurrentProfileId, session: DbSession) -> object:
    screening = repository.get_health_screening(session, profile_id)
    if screening is None:
        raise ApiError(
            code="SCREENING_NOT_FOUND",
            message="Es wurden noch keine Angaben zur Gesundheitssituation gespeichert.",
            status_code=404,
        )
    return screening


@router.put("/health-screening", response_model=HealthScreeningResponse)
def put_health_screening(
    payload: HealthScreeningUpdate, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return service.update_health_screening(session, profile_id, payload)
