# mypy: disable-error-code="type-arg"
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.pantry_aware_shopping import service
from app.modules.pantry_aware_shopping.schemas import ApplyRequest, PreviewRequest

router = APIRouter(tags=["pantry-aware-shopping"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/api/v1/pantry-aware-shopping/eligible-lists")
def eligible_lists(profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.eligible_lists(session, profile_id)


@router.post("/api/v1/pantry-aware-shopping/preview")
def preview(payload: PreviewRequest, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.preview(session, profile_id, payload)


@router.post("/api/v1/pantry-aware-shopping/apply")
def apply(payload: ApplyRequest, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.apply(session, profile_id, payload)


@router.post("/api/v1/shopping-lists/{shopping_list_id}/pantry-aware-preview")
def reconcile_preview(
    shopping_list_id: UUID,
    payload: PreviewRequest,
    profile_id: CurrentProfileId,
    session: DbSession,
) -> dict:
    request = payload.model_copy(
        update={
            "source_type": "shopping_list_reconciliation",
            "target_shopping_list_id": shopping_list_id,
            "create_new_list": False,
        }
    )
    return service.preview(session, profile_id, request)


@router.post("/api/v1/shopping-lists/{shopping_list_id}/pantry-aware-apply")
def reconcile_apply(
    shopping_list_id: UUID,
    payload: ApplyRequest,
    profile_id: CurrentProfileId,
    session: DbSession,
) -> dict:
    request = payload.model_copy(
        update={
            "preview": payload.preview.model_copy(
                update={
                    "source_type": "shopping_list_reconciliation",
                    "target_shopping_list_id": shopping_list_id,
                    "create_new_list": False,
                }
            )
        }
    )
    return service.apply(session, profile_id, request)
