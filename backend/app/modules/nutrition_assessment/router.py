from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.nutrition_assessment import service
from app.modules.nutrition_assessment.schemas import (
    AssessmentCreateRequest,
    AssessmentHistoryResponse,
    AssessmentResponse,
)

router = APIRouter(prefix="/api/v1/assessments", tags=["nutrition assessment"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def post_assessment(
    payload: AssessmentCreateRequest,
    profile_id: CurrentProfileId,
    session: DbSession,
) -> object:
    return service.create_assessment(session, profile_id, payload.client_request_id)


@router.get("", response_model=AssessmentHistoryResponse)
def read_assessment_history(
    profile_id: CurrentProfileId,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> object:
    return service.assessment_history(session, profile_id, limit=limit, offset=offset)


@router.get("/latest", response_model=AssessmentResponse)
def read_latest_assessment(profile_id: CurrentProfileId, session: DbSession) -> object:
    return service.require_latest_assessment(session, profile_id)


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def read_assessment(
    assessment_id: UUID, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return service.require_assessment(session, profile_id, assessment_id)
