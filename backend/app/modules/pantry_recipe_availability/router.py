# mypy: disable-error-code="type-arg"
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.current_profile import CurrentProfileId
from app.database.session import get_db
from app.modules.pantry_recipe_availability import service

router = APIRouter(prefix="/api/v1/recipes", tags=["pantry-recipe-availability"])
DbSession = Annotated[Session, Depends(get_db)]
DateMode = Literal["include_all", "exclude_past_use_by", "exclude_all_past_dates"]


@router.get("/pantry-availability")
def recipe_summaries(
    profile_id: CurrentProfileId,
    session: DbSession,
    query: str | None = None,
    include_archived: bool = False,
    availability_state: str | None = None,
    minimum_possible_portions: str | None = None,
    sort: str = "availability_state",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    return service.summaries(
        session,
        profile_id,
        query=query,
        include_archived=include_archived,
        state=availability_state,
        minimum_portions=_decimal(minimum_possible_portions),
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/{recipe_id}/pantry-availability")
def recipe_availability(
    recipe_id: UUID,
    profile_id: CurrentProfileId,
    session: DbSession,
    portion_count: str = "1",
    include_optional_ingredients: bool = False,
    date_handling_mode: DateMode = "include_all",
    include_lot_details: bool = True,
) -> dict:
    portions = _decimal(portion_count)
    return service.availability(
        session,
        profile_id,
        recipe_id,
        portions if portions is not None else Decimal(1),
        include_optional_ingredients,
        date_handling_mode,
        include_lot_details,
    )


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.strip().replace(",", "."))
    except Exception:
        return Decimal(-1)
