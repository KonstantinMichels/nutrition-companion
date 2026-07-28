from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.core.errors import ApiError
from app.database.session import get_db
from app.modules.foods import open_food_facts, repository, service
from app.modules.foods.nutrient_catalog import NUTRIENT_BY_CODE, NUTRIENTS
from app.modules.foods.schemas import (
    ArchiveResponse,
    BarcodeImportRequest,
    BarcodePreviewResponse,
    DuplicateResponse,
    FoodListResponse,
    FoodResponse,
    FoodWrite,
    NutrientCatalogResponse,
    PermanentDeleteResponse,
)

router = APIRouter(prefix="/api/v1", tags=["foods"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/nutrients", response_model=list[NutrientCatalogResponse])
def nutrients(
    category: str | None = None, basic_only: bool = False, active_only: bool = True
) -> list[object]:
    return [
        n
        for n in NUTRIENTS
        if (not category or n.category == category)
        and (not basic_only or n.basic_form)
        and (not active_only or n.active)
    ]


@router.get("/nutrients/{code}", response_model=NutrientCatalogResponse)
def nutrient(code: str) -> object:
    item = NUTRIENT_BY_CODE.get(code)
    if item is None:
        raise ApiError("NUTRIENT_NOT_FOUND", "Der Nährstoff wurde nicht gefunden.", 404)
    return item


@router.get("/foods", response_model=FoodListResponse)
def foods(
    profile_id: CurrentProfileId,
    session: DbSession,
    query: str | None = None,
    category: str | None = None,
    include_archived: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> FoodListResponse:
    items, total = repository.list_foods(
        session,
        profile_id,
        query=query,
        category=category,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return FoodListResponse(
        items=[service.serialize(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/foods/duplicates", response_model=DuplicateResponse)
def duplicates(
    name: str, profile_id: CurrentProfileId, session: DbSession, brand: str | None = None
) -> DuplicateResponse:
    return DuplicateResponse(
        items=[
            service.serialize(item)
            for item in repository.duplicates(session, profile_id, name, brand)
        ]
    )


@router.get("/foods/barcode/{code}", response_model=BarcodePreviewResponse)
def barcode_preview(code: str, _profile_id: CurrentProfileId) -> object:
    return open_food_facts.lookup_barcode(code)


@router.post(
    "/foods/barcode/{code}/import",
    response_model=FoodResponse,
    status_code=status.HTTP_201_CREATED,
)
def barcode_import(
    code: str,
    payload: BarcodeImportRequest,
    profile_id: CurrentProfileId,
    session: DbSession,
) -> FoodResponse:
    if open_food_facts.normalize_barcode(code) != payload.preview.barcode:
        raise ApiError(
            "INVALID_BARCODE",
            "Der bestätigte Barcode stimmt nicht mit der Vorschau überein.",
            422,
        )
    return service.import_barcode_food(session, profile_id, payload)


@router.post("/foods", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
def create(payload: FoodWrite, profile_id: CurrentProfileId, session: DbSession) -> FoodResponse:
    return service.create_food(session, profile_id, payload)


@router.get("/foods/{food_id}", response_model=FoodResponse)
def detail(food_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> FoodResponse:
    return service.serialize(service.require_food(session, profile_id, food_id))


@router.put("/foods/{food_id}", response_model=FoodResponse)
def update(
    food_id: UUID, payload: FoodWrite, profile_id: CurrentProfileId, session: DbSession
) -> FoodResponse:
    return service.update_food(session, profile_id, food_id, payload)


@router.delete("/foods/{food_id}", response_model=ArchiveResponse)
def archive(food_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> ArchiveResponse:
    food = service.archive_food(session, profile_id, food_id)
    return ArchiveResponse(
        id=food.id, archived=True, message_de="Das Lebensmittel wurde archiviert, nicht gelöscht."
    )


@router.post("/foods/{food_id}/restore", response_model=FoodResponse)
def restore(food_id: UUID, profile_id: CurrentProfileId, session: DbSession) -> FoodResponse:
    return service.restore_food(session, profile_id, food_id)


@router.delete("/foods/{food_id}/permanent", response_model=PermanentDeleteResponse)
def permanently_delete(
    food_id: UUID, profile_id: CurrentProfileId, session: DbSession
) -> PermanentDeleteResponse:
    deleted_id = service.permanently_delete_food(session, profile_id, food_id)
    return PermanentDeleteResponse(
        id=deleted_id,
        deleted=True,
        message_de="Das Lebensmittel und seine Nährwerte wurden endgültig gelöscht.",
    )
