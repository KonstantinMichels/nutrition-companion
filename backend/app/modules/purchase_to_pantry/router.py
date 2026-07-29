# mypy: disable-error-code="type-arg"
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.purchase_to_pantry import service
from app.modules.purchase_to_pantry.schemas import ApplyRequest, PreviewRequest

router = APIRouter(prefix="/api/v1/shopping-lists/{list_id}", tags=["purchase-to-pantry"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/pantry-handoff-eligibility")
def eligibility(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.eligibility(session, profile_id, list_id)


@router.post("/pantry-handoff-preview")
def preview(
    list_id: UUID, payload: PreviewRequest, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.preview(session, profile_id, list_id, payload)


@router.post("/pantry-handoff", status_code=status.HTTP_201_CREATED)
def apply(
    list_id: UUID, payload: ApplyRequest, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.apply(session, profile_id, list_id, payload)


@router.get("/pantry-handoffs")
def history(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> list[dict]:
    return service.history(session, profile_id, list_id)


@router.get("/items/{item_id}/pantry-handoffs")
def item_history(
    list_id: UUID, item_id: UUID, profile_id: CurrentProfileId, session: DbSession
) -> list[dict]:
    return service.history(session, profile_id, list_id, item_id)


@router.get("/pantry-handoffs/{handoff_id}")
def detail(
    list_id: UUID, handoff_id: UUID, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.handoff_detail(session, profile_id, list_id, handoff_id)
