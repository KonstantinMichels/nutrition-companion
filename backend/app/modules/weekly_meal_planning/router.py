from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.weekly_meal_planning import service
from app.modules.weekly_meal_planning.schemas import (
    MealTransferRequest,
    MealTransferResponse,
    WeeklyMealPlanResponse,
)

router = APIRouter(prefix="/api/v1/weekly-meal-plans", tags=["weekly-meal-planning"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=WeeklyMealPlanResponse)
def weekly_overview(
    profile_id: CurrentProfileId,
    session: DbSession,
    anchor_date: date = Query(...),
    include_archived_metadata: bool = True,
) -> WeeklyMealPlanResponse:
    return service.overview(
        session, profile_id, anchor_date, include_archived_metadata=include_archived_metadata
    )


@router.post("/actions/copy-meal", response_model=MealTransferResponse)
def copy_meal(
    payload: MealTransferRequest, profile_id: CurrentProfileId, session: DbSession
) -> MealTransferResponse:
    return service.transfer_meal(session, profile_id, payload, move=False)


@router.post("/actions/move-meal", response_model=MealTransferResponse)
def move_meal(
    payload: MealTransferRequest, profile_id: CurrentProfileId, session: DbSession
) -> MealTransferResponse:
    return service.transfer_meal(session, profile_id, payload, move=True)
