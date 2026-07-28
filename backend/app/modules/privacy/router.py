from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.privacy import repository, service
from app.modules.privacy.schemas import (
    ConsentCreate,
    ConsentResponse,
    DeletionConfirmation,
    DeletionResponse,
    PrivacyExportResponse,
    ProcessingPurposeResponse,
)

router = APIRouter(tags=["privacy"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/api/v1/privacy/purposes", response_model=list[ProcessingPurposeResponse])
def read_purposes(session: DbSession) -> object:
    return repository.list_purposes(session)


@router.get("/api/v1/privacy/consents", response_model=list[ConsentResponse])
def read_consents(profile_id: CurrentProfileId, session: DbSession) -> object:
    return repository.list_consents(session, profile_id)


@router.post(
    "/api/v1/privacy/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consent(
    payload: ConsentCreate, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return service.grant_consent(session, profile_id, payload)


@router.post(
    "/api/v1/privacy/consents/{consent_id}/withdraw",
    response_model=ConsentResponse,
)
def withdraw_consent(consent_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> object:
    return service.withdraw_consent(session, profile_id, consent_id)


@router.get("/api/v1/privacy/export", response_model=PrivacyExportResponse)
def export_data(profile_id: CurrentProfileId, session: DbSession) -> object:
    return service.build_export(session, profile_id)


@router.delete("/api/v1/assessments", response_model=DeletionResponse)
def delete_assessments(
    _confirmation: DeletionConfirmation, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return service.delete_assessment_history(session, profile_id)


@router.delete("/api/v1/profile", response_model=DeletionResponse)
def delete_profile(
    _confirmation: DeletionConfirmation, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return service.delete_complete_profile(session, profile_id)


@router.delete("/api/v1/privacy/local-profile-data", response_model=DeletionResponse)
def delete_profile_via_privacy_path(
    _confirmation: DeletionConfirmation, profile_id: CurrentProfileId, session: DbSession
) -> object:
    return service.delete_complete_profile(session, profile_id)
