# mypy: disable-error-code="type-arg"
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.shopping_lists import service
from app.modules.shopping_lists.schemas import (
    GenerationRequest,
    ItemCreate,
    ItemPatch,
    ListCreate,
    ListPatch,
    RefreshRequest,
    ReorderRequest,
)

router = APIRouter(prefix="/api/v1/shopping-lists", tags=["shopping-lists"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def lists(
    profile_id: CurrentProfileId,
    session: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    source_type: str | None = None,
    include_archived: bool = False,
    query: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort: str = "updated",
) -> dict:
    return service.list_all(
        session,
        profile_id,
        status_filter,
        source_type,
        include_archived,
        query,
        page,
        page_size,
        sort,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create(payload: ListCreate, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.create(session, profile_id, payload)


@router.post("/generation-preview")
def generation_preview(
    payload: GenerationRequest, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.calculate(session, profile_id, payload)


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate(payload: GenerationRequest, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.generate(session, profile_id, payload)


@router.get("/{list_id}")
def detail(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.detail(session, profile_id, list_id)


@router.patch("/{list_id}")
def update(
    list_id: UUID, payload: ListPatch, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.update(session, profile_id, list_id, payload)


@router.post("/{list_id}/items", status_code=status.HTTP_201_CREATED)
def add_item(
    list_id: UUID, payload: ItemCreate, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.add_item(session, profile_id, list_id, payload)


@router.patch("/{list_id}/items/{item_id}")
def update_item(
    list_id: UUID,
    item_id: UUID,
    payload: ItemPatch,
    profile_id: CurrentProfileId,
    session: DbSession,
) -> dict:
    return service.update_item(session, profile_id, list_id, item_id, payload)


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    list_id: UUID, item_id: UUID, profile_id: CurrentProfileId, session: DbSession
) -> Response:
    service.remove_item(session, profile_id, list_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{list_id}/items/reorder")
def reorder(
    list_id: UUID, payload: ReorderRequest, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.reorder(session, profile_id, list_id, payload.item_ids)


@router.post("/{list_id}/items/{item_id}/check")
def check(list_id: UUID, item_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.update_item(session, profile_id, list_id, item_id, ItemPatch(is_checked=True))


@router.post("/{list_id}/items/{item_id}/uncheck")
def uncheck(list_id: UUID, item_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.update_item(session, profile_id, list_id, item_id, ItemPatch(is_checked=False))


@router.post("/{list_id}/refresh-preview")
def refresh_preview(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.refresh_preview(session, profile_id, list_id)


@router.post("/{list_id}/refresh")
def refresh(
    list_id: UUID, payload: RefreshRequest, profile_id: CurrentProfileId, session: DbSession
) -> dict:
    return service.refresh(session, profile_id, list_id, payload.preview_version)


@router.post("/{list_id}/complete")
def complete(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.set_state(session, profile_id, list_id, "complete")


@router.post("/{list_id}/reopen")
def reopen(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.set_state(session, profile_id, list_id, "reopen")


@router.delete("/{list_id}")
def archive(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.set_state(session, profile_id, list_id, "archive")


@router.post("/{list_id}/restore")
def restore(list_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> dict:
    return service.set_state(session, profile_id, list_id, "restore")
