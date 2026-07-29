from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.recipes import repository, service
from app.modules.recipes.schemas import (
    ArchiveResponse,
    PermanentDeleteResponse,
    RecipeListResponse,
    RecipeResponse,
    RecipeWrite,
    ScaleResponse,
)

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=RecipeListResponse)
def recipes(
    profile_id: CurrentProfileId,
    session: DbSession,
    query: str | None = None,
    tag: str | None = None,
    include_archived: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> RecipeListResponse:
    items, total = repository.list_recipes(
        session,
        profile_id,
        query=query,
        tag=tag,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return RecipeListResponse(
        items=[service.serialize(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: RecipeWrite, profile_id: CurrentProfileId, session: DbSession
) -> RecipeResponse:
    return service.create(session, profile_id, payload)


@router.get("/{recipe_id}", response_model=RecipeResponse)
def detail(recipe_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> RecipeResponse:
    return service.serialize(service.require(session, profile_id, recipe_id))


@router.put("/{recipe_id}", response_model=RecipeResponse)
def update(
    recipe_id: UUID, payload: RecipeWrite, profile_id: CurrentProfileId, session: DbSession
) -> RecipeResponse:
    return service.update(session, profile_id, recipe_id, payload)


@router.get("/{recipe_id}/scale", response_model=ScaleResponse)
def scale(
    recipe_id: UUID,
    servings: Annotated[Decimal, Query(gt=0)],
    profile_id: CurrentProfileId,
    session: DbSession,
) -> object:
    return service.scaled(service.require(session, profile_id, recipe_id), servings)


@router.post(
    "/{recipe_id}/duplicate", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED
)
def duplicate(recipe_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> RecipeResponse:
    return service.duplicate(session, profile_id, recipe_id)


@router.delete("/{recipe_id}", response_model=ArchiveResponse)
def archive(recipe_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> ArchiveResponse:
    item = service.archive(session, profile_id, recipe_id)
    return ArchiveResponse(
        id=item.id, archived=True, message_de="Das Rezept wurde archiviert, nicht gelöscht."
    )


@router.delete("/{recipe_id}/permanent", response_model=PermanentDeleteResponse)
def permanently_delete(
    recipe_id: UUID, profile_id: CurrentProfileId, session: DbSession
) -> PermanentDeleteResponse:
    deleted_id = service.permanently_delete(session, profile_id, recipe_id)
    return PermanentDeleteResponse(
        id=deleted_id,
        deleted=True,
        message_de="Das Rezept wurde dauerhaft gelöscht.",
    )


@router.post("/{recipe_id}/restore", response_model=RecipeResponse)
def restore(recipe_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> RecipeResponse:
    return service.restore(session, profile_id, recipe_id)
