# mypy: disable-error-code="type-arg"
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.meal_plan_automation import draft_service, service
from app.modules.meal_plan_automation.schemas import ApplyRequest, GenerateRequest, PreferencesWrite

router = APIRouter(prefix="/api/v1/meal-plan-automation", tags=["meal-plan-automation"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/preferences")
def preferences(
    profile_id: CurrentProfileId, session: Db, include_archived: bool = False
) -> list[dict]:
    return service.list_all(session, profile_id, include_archived)


@router.post("/preferences", status_code=status.HTTP_201_CREATED)
def create(payload: PreferencesWrite, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.create(session, profile_id, payload)


@router.get("/preferences/{preferences_id}")
def detail(preferences_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.serialize(service.get(session, profile_id, preferences_id))


@router.patch("/preferences/{preferences_id}")
def update_preferences(
    preferences_id: UUID,
    payload: PreferencesWrite,
    profile_id: CurrentProfileId,
    session: Db,
) -> dict:
    return service.replace(session, profile_id, preferences_id, payload)


@router.delete("/preferences/{preferences_id}")
def archive(preferences_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.archive(session, profile_id, preferences_id)


@router.post("/preferences/{preferences_id}/restore")
def restore(preferences_id: UUID, profile_id: CurrentProfileId, session: Db) -> dict:
    return service.archive(session, profile_id, preferences_id, True)


@router.post("/candidates")
def candidates(payload: GenerateRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    return draft_service.generate(session, profile_id, payload)


@router.post("/generate")
def generate(payload: GenerateRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    return draft_service.generate(session, profile_id, payload)


@router.post("/recalculate")
def recalculate(payload: GenerateRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    return draft_service.generate(session, profile_id, payload)


@router.post("/optimize")
def optimize(payload: GenerateRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    if payload.generation_engine in {None, "greedy"}:
        payload = payload.model_copy(update={"generation_engine": "optimizer_strict"})
    return draft_service.generate(session, profile_id, payload)


@router.post("/regenerate-slot")
def regenerate(payload: GenerateRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    return draft_service.generate(session, profile_id, payload)


@router.post("/apply")
def apply(payload: ApplyRequest, profile_id: CurrentProfileId, session: Db) -> dict:
    return draft_service.apply(session, profile_id, payload)


@router.get("/applications")
def applications(profile_id: CurrentProfileId, session: Db) -> list[dict]:
    return service.applications(session, profile_id)
