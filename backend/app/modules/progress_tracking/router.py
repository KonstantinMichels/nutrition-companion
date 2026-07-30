# mypy: disable-error-code="type-arg"
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.core.errors import ApiError
from app.database.session import get_db
from app.modules.progress_tracking import service
from app.modules.progress_tracking.schemas import (
    CompositionWrite,
    GoalWrite,
    MeasurementWrite,
    WeightWrite,
)

router = APIRouter(prefix="/api/v1/progress", tags=["progress-tracking"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/overview")
def overview(
    profile_id: CurrentProfileId,
    session: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    rolling_window_days: int = Query(7, ge=7, le=28),
) -> dict:
    if rolling_window_days not in {7, 14, 28}:
        raise ApiError(
            code="PROGRESS_INVALID_ROLLING_WINDOW",
            message="Das Trendfenster muss 7, 14 oder 28 Tage betragen.",
            status_code=422,
        )
    return service.overview(session, profile_id, date_from, date_to, rolling_window_days)


@router.get("/weight-observations")
def weights(
    profile_id: CurrentProfileId,
    session: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort: str = "observed_at_desc",
) -> dict:
    return service.list_weights(
        session,
        profile_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        sort=sort,
    )


@router.post("/weight-observations", status_code=status.HTTP_201_CREATED)
def create_weight(payload: WeightWrite, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.create_weight(session, profile_id, payload)


@router.get("/weight-observations/{item_id}")
def weight(item_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.weight_detail(session, profile_id, item_id)


@router.patch("/weight-observations/{item_id}")
def edit_weight(
    item_id: UUID, payload: WeightWrite, profile_id: CurrentProfileId, session: Db
) -> dict:
    return service.update_weight(session, profile_id, item_id, payload)


@router.delete("/weight-observations/{item_id}")
def delete_weight(
    item_id: UUID, profile_id: CurrentProfileId, session: Db, expected_version: int | None = None
) -> dict:
    return service.delete_weight(session, profile_id, item_id, expected_version)


@router.get("/body-measurements")
def measurements(
    profile_id: CurrentProfileId,
    session: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    measurement_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort: str = "observed_at_desc",
) -> dict:
    return service.list_measurements(
        session,
        profile_id,
        date_from=date_from,
        date_to=date_to,
        measurement_type=measurement_type,
        page=page,
        page_size=page_size,
        sort=sort,
    )


@router.post("/body-measurements", status_code=201)
def create_measurement(
    payload: MeasurementWrite, profile_id: CurrentProfileId, session: Db
) -> dict:
    return service.create_measurement(session, profile_id, payload)


@router.get("/body-measurements/{item_id}")
def measurement(item_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.measurement_detail(session, profile_id, item_id)


@router.patch("/body-measurements/{item_id}")
def edit_measurement(
    item_id: UUID, payload: MeasurementWrite, profile_id: CurrentProfileId, session: Db
) -> dict:
    return service.update_measurement(session, profile_id, item_id, payload)


@router.delete("/body-measurements/{item_id}")
def delete_measurement(
    item_id: UUID, profile_id: CurrentProfileId, session: Db, expected_version: int | None = None
) -> dict:
    return service.delete_measurement(session, profile_id, item_id, expected_version)


@router.get("/body-composition")
def compositions(
    profile_id: CurrentProfileId,
    session: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    measurement_method: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort: str = "observed_at_desc",
) -> dict:
    return service.list_composition(
        session,
        profile_id,
        date_from=date_from,
        date_to=date_to,
        measurement_method=measurement_method,
        page=page,
        page_size=page_size,
        sort=sort,
    )


@router.post("/body-composition", status_code=201)
def create_composition(
    payload: CompositionWrite, profile_id: CurrentProfileId, session: Db
) -> dict:
    return service.create_composition(session, profile_id, payload)


@router.get("/body-composition/{item_id}")
def composition(item_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.composition_detail(session, profile_id, item_id)


@router.patch("/body-composition/{item_id}")
def edit_composition(
    item_id: UUID, payload: CompositionWrite, profile_id: CurrentProfileId, session: Db
) -> dict:
    return service.update_composition(session, profile_id, item_id, payload)


@router.delete("/body-composition/{item_id}")
def delete_composition(
    item_id: UUID, profile_id: CurrentProfileId, session: Db, expected_version: int | None = None
) -> dict:
    return service.delete_composition(session, profile_id, item_id, expected_version)


@router.get("/goals")
def goals(profile_id: CurrentProfileId, session: Db) -> list[dict]:
    return service.list_goals(session, profile_id)


@router.post("/goals", status_code=201)
def create_goal(payload: GoalWrite, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.create_goal(session, profile_id, payload)


@router.get("/goals/{goal_id}")
def goal(goal_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.goal_detail(session, profile_id, goal_id)


@router.patch("/goals/{goal_id}")
def edit_goal(goal_id: UUID, payload: GoalWrite, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.update_goal(session, profile_id, goal_id, payload)


@router.post("/goals/{goal_id}/complete")
def complete(
    goal_id: UUID, profile_id: CurrentProfileId, session: Db, expected_version: int | None = None
) -> dict:
    return service.set_goal_status(session, profile_id, goal_id, "completed", expected_version)


@router.post("/goals/{goal_id}/cancel")
def cancel(
    goal_id: UUID, profile_id: CurrentProfileId, session: Db, expected_version: int | None = None
) -> dict:
    return service.set_goal_status(session, profile_id, goal_id, "cancelled", expected_version)
