# mypy: disable-error-code="type-arg"
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db

from . import repository, service
from .schemas import (
    ConfirmWholeMeal,
    DayCreate,
    DayPatch,
    EntryWrite,
    FinalizeWrite,
    FromPlan,
    LinkDailyPlan,
    MealWrite,
    OutcomeWrite,
    ReorderMeals,
)

router = APIRouter(prefix="/api/v1", tags=["consumption-tracking"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/consumption-days")
def list_days(
    profile_id: CurrentProfileId,
    db: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    completeness_attestation: str | None = None,
    has_daily_plan: bool | None = None,
    has_unresolved_entries: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    sort: str = "date_desc",
) -> dict:
    return service.history(
        db,
        profile_id,
        date_from,
        date_to,
        status_filter,
        completeness_attestation,
        has_daily_plan,
        has_unresolved_entries,
        page,
        page_size,
        sort,
    )


@router.post("/consumption-days", status_code=status.HTTP_201_CREATED)
def create(payload: DayCreate, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.create_day(db, profile_id, payload)


@router.post("/consumption-days/from-daily-plan", status_code=status.HTTP_201_CREATED)
def from_plan(payload: FromPlan, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.from_plan(db, profile_id, payload)


@router.get("/consumption-days/by-date/{value}")
def by_date(value: date, profile_id: CurrentProfileId, db: Db) -> dict:
    day = repository.by_date(db, profile_id, value)
    if day is None:
        raise service.error(
            "CONSUMPTION_DAY_NOT_FOUND", "Für diesen Tag wurde noch kein Verzehr erfasst.", 404
        )
    return service.detail(day)


@router.get("/consumption-days/{day_id}")
def detail(day_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.detail(service.require_day(db, profile_id, day_id))


@router.patch("/consumption-days/{day_id}")
def patch(day_id: UUID, payload: DayPatch, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.patch_day(db, profile_id, day_id, payload)


@router.post("/consumption-days/{day_id}/link-daily-plan")
def link_daily_plan(
    day_id: UUID,
    payload: LinkDailyPlan,
    profile_id: CurrentProfileId,
    db: Db,
) -> dict:
    return service.link_daily_plan(db, profile_id, day_id, payload)


@router.delete("/consumption-days/{day_id}")
def delete_day(day_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.delete_day(db, profile_id, day_id)


@router.post("/consumption-days/{day_id}/meals", status_code=201)
def add_meal(day_id: UUID, payload: MealWrite, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.add_meal(db, profile_id, day_id, payload)


@router.patch("/consumption-days/{day_id}/meals/{meal_id}")
def update_meal(
    day_id: UUID, meal_id: UUID, payload: MealWrite, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.update_meal(db, profile_id, day_id, meal_id, payload)


@router.delete("/consumption-days/{day_id}/meals/{meal_id}")
def delete_meal(
    day_id: UUID, meal_id: UUID, profile_id: CurrentProfileId, db: Db, confirm: bool = False
) -> dict:
    return service.delete_meal(db, profile_id, day_id, meal_id, confirm)


@router.post("/consumption-days/{day_id}/meals/reorder")
def reorder(day_id: UUID, payload: ReorderMeals, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.reorder_meals(db, profile_id, day_id, payload)


@router.post("/consumption-days/{day_id}/plan-meals/{plan_meal_id}/confirm")
def confirm_whole_meal(
    day_id: UUID,
    plan_meal_id: UUID,
    payload: ConfirmWholeMeal,
    profile_id: CurrentProfileId,
    db: Db,
) -> dict:
    return service.confirm_whole_meal(db, profile_id, day_id, plan_meal_id, payload)


@router.post("/consumption-days/{day_id}/entries/preview")
def preview_entry(day_id: UUID, payload: EntryWrite, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.preview_entry(db, profile_id, day_id, payload)


@router.post("/consumption-days/{day_id}/entries", status_code=201)
def add_entry(day_id: UUID, payload: EntryWrite, profile_id: CurrentProfileId, db: Db) -> dict:
    return service._entry_dict(service.create_entry(db, profile_id, day_id, payload))


@router.get("/consumption-days/{day_id}/entries/{entry_id}")
def get_entry(day_id: UUID, entry_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    day = service.require_day(db, profile_id, day_id)
    item = next((e for m in day.meals for e in m.entries if e.id == entry_id), None)
    if item is None:
        raise service.error("CONSUMPTION_ENTRY_NOT_FOUND", "Der Eintrag wurde nicht gefunden.", 404)
    return service._entry_dict(item)


@router.patch("/consumption-days/{day_id}/entries/{entry_id}")
def update_entry(
    day_id: UUID, entry_id: UUID, payload: EntryWrite, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.update_entry(db, profile_id, day_id, entry_id, payload)


@router.delete("/consumption-days/{day_id}/entries/{entry_id}")
def delete_entry(day_id: UUID, entry_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.delete_entry(db, profile_id, day_id, entry_id)


@router.post("/consumption-days/{day_id}/planned-entry-outcomes/preview")
def preview_outcome(
    day_id: UUID, plan_entry_id: UUID, payload: OutcomeWrite, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.preview_outcome(db, profile_id, day_id, plan_entry_id, payload)


@router.put("/consumption-days/{day_id}/planned-entry-outcomes/{plan_entry_id}")
def outcome(
    day_id: UUID, plan_entry_id: UUID, payload: OutcomeWrite, profile_id: CurrentProfileId, db: Db
) -> dict:
    return service.apply_outcome(db, profile_id, day_id, plan_entry_id, payload)


@router.delete("/consumption-days/{day_id}/planned-entry-outcomes/{plan_entry_id}")
def delete_outcome(
    day_id: UUID, plan_entry_id: UUID, profile_id: CurrentProfileId, db: Db, confirm: bool = False
) -> dict:
    return service.delete_outcome(db, profile_id, day_id, plan_entry_id, confirm)


@router.post("/consumption-days/{day_id}/finalize")
def finalize(day_id: UUID, payload: FinalizeWrite, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.finalize(db, profile_id, day_id, payload)


@router.post("/consumption-days/{day_id}/reopen")
def reopen(day_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.reopen(db, profile_id, day_id)


@router.get("/consumption-days/{day_id}/summary")
def summary(day_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.summary(service.require_day(db, profile_id, day_id))


@router.get("/consumption-days/{day_id}/planned-vs-actual")
def planned_actual(day_id: UUID, profile_id: CurrentProfileId, db: Db) -> dict:
    day = service.require_day(db, profile_id, day_id)
    return service.planned_vs_actual(day)


@router.get("/consumption/weekly-summary")
def weekly(week_start: date, profile_id: CurrentProfileId, db: Db) -> dict:
    return service.weekly(db, profile_id, week_start)


@router.get("/consumption/history")
def history(
    profile_id: CurrentProfileId,
    db: Db,
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    completeness_attestation: str | None = None,
    has_daily_plan: bool | None = None,
    has_unresolved_entries: bool | None = None,
    page: int = 1,
    page_size: int = 30,
    sort: str = "date_desc",
) -> dict:
    return service.history(
        db,
        profile_id,
        date_from,
        date_to,
        status_filter,
        completeness_attestation,
        has_daily_plan,
        has_unresolved_entries,
        page,
        page_size,
        sort,
    )
