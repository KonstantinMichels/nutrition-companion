from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.daily_meal_planning import repository, service
from app.modules.daily_meal_planning.schemas import (
    ArchivePlanResponse,
    DailyPlanListResponse,
    DailyPlanResponse,
    DailyPlanWrite,
    DuplicatePlanRequest,
)

router = APIRouter(prefix="/api/v1/daily-meal-plans", tags=["daily-meal-planning"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=DailyPlanListResponse)
def list_daily_plans(
    profile_id: CurrentProfileId,
    session: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    include_archived: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> DailyPlanListResponse:
    return service.list_plans(
        session,
        profile_id,
        date_from=date_from,
        date_to=date_to,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )


@router.post("/preview", response_model=DailyPlanResponse)
def preview(
    payload: DailyPlanWrite, profile_id: CurrentProfileId, session: DbSession
) -> DailyPlanResponse:
    return service.preview(session, profile_id, payload)


@router.get("/by-date/{plan_date}", response_model=DailyPlanResponse)
def by_date(plan_date: date, profile_id: CurrentProfileId, session: DbSession) -> DailyPlanResponse:
    plan = repository.by_date(session, profile_id, plan_date)
    if plan is None:
        raise service._error(
            "DAILY_PLAN_NOT_FOUND", "Für diesen Tag ist noch kein Tagesplan vorhanden.", 404
        )
    return service.serialize(plan)


@router.post("", response_model=DailyPlanResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: DailyPlanWrite, profile_id: CurrentProfileId, session: DbSession
) -> DailyPlanResponse:
    return service.create(session, profile_id, payload)


@router.get("/{plan_id}", response_model=DailyPlanResponse)
def detail(plan_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> DailyPlanResponse:
    return service.serialize(service.require(session, profile_id, plan_id))


@router.put("/{plan_id}", response_model=DailyPlanResponse)
def update(
    plan_id: UUID, payload: DailyPlanWrite, profile_id: CurrentProfileId, session: DbSession
) -> DailyPlanResponse:
    return service.update(session, profile_id, plan_id, payload)


@router.delete("/{plan_id}", response_model=ArchivePlanResponse)
def archive(plan_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> ArchivePlanResponse:
    plan = service.archive(session, profile_id, plan_id)
    return ArchivePlanResponse(
        id=plan.id, archived=True, message_de="Der Tagesplan wurde archiviert."
    )


@router.post("/{plan_id}/restore", response_model=DailyPlanResponse)
def restore(plan_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> DailyPlanResponse:
    return service.restore(session, profile_id, plan_id)


@router.post(
    "/{plan_id}/duplicate", response_model=DailyPlanResponse, status_code=status.HTTP_201_CREATED
)
def duplicate(
    plan_id: UUID, payload: DuplicatePlanRequest, profile_id: CurrentProfileId, session: DbSession
) -> DailyPlanResponse:
    return service.duplicate(session, profile_id, plan_id, payload)
