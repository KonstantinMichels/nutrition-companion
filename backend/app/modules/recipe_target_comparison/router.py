from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.recipe_target_comparison import service
from app.modules.recipe_target_comparison.schemas import (
    ComparableAssessmentsResponse,
    TargetComparisonResponse,
)

router = APIRouter(tags=["recipe target comparison"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/api/v1/recipes/{recipe_id}/target-comparison",
    response_model=TargetComparisonResponse,
)
def target_comparison(
    recipe_id: UUID,
    profile_id: CurrentProfileId,
    session: DbSession,
    assessment_id: UUID | None = None,
    portion_count: Annotated[Decimal, Query(gt=0, le=100)] = Decimal(1),
) -> TargetComparisonResponse:
    return service.compare(session, profile_id, recipe_id, assessment_id, portion_count)


@router.get("/api/v1/assessments/comparable", response_model=ComparableAssessmentsResponse)
def assessments_for_comparison(
    profile_id: CurrentProfileId, session: DbSession
) -> ComparableAssessmentsResponse:
    return service.comparable_assessments(session, profile_id)
