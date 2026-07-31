from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, selectinload

from .models import (
    ConsumptionDay,
    ConsumptionEntry,
    ConsumptionMeal,
    PlannedEntryConsumptionOutcome,
)

LOAD = (
    selectinload(ConsumptionDay.meals)
    .selectinload(ConsumptionMeal.entries)
    .selectinload(ConsumptionEntry.nutrient_snapshots),
    selectinload(ConsumptionDay.outcomes).selectinload(PlannedEntryConsumptionOutcome.entries),
    selectinload(ConsumptionDay.assessment),
    selectinload(ConsumptionDay.training_day_adjustment),
)


def get(
    session: Session, profile_id: UUID, day_id: UUID, *, lock: bool = False
) -> ConsumptionDay | None:
    query = (
        select(ConsumptionDay)
        .where(ConsumptionDay.id == day_id, ConsumptionDay.owner_profile_id == profile_id)
        .options(*LOAD)
    )
    if lock:
        query = query.with_for_update()
    return session.scalar(query)


def by_date(session: Session, profile_id: UUID, value: date) -> ConsumptionDay | None:
    return session.scalar(
        select(ConsumptionDay)
        .where(
            ConsumptionDay.owner_profile_id == profile_id, ConsumptionDay.consumption_date == value
        )
        .options(*LOAD)
    )


def list_days(
    session: Session,
    profile_id: UUID,
    date_from: date | None,
    date_to: date | None,
    status: str | None,
    completeness: str | None,
    has_daily_plan: bool | None,
    has_unresolved_entries: bool | None,
    page: int,
    page_size: int,
    sort: str = "date_desc",
) -> tuple[list[ConsumptionDay], int]:
    filters = [ConsumptionDay.owner_profile_id == profile_id]
    if date_from:
        filters.append(ConsumptionDay.consumption_date >= date_from)
    if date_to:
        filters.append(ConsumptionDay.consumption_date <= date_to)
    if status:
        filters.append(ConsumptionDay.status == status)
    if completeness:
        filters.append(ConsumptionDay.completeness_attestation == completeness)
    if has_daily_plan is not None:
        filters.append(
            ConsumptionDay.source_daily_plan_id.is_not(None)
            if has_daily_plan
            else ConsumptionDay.source_daily_plan_id.is_(None)
        )
    if has_unresolved_entries is not None:
        unresolved = exists(
            select(ConsumptionEntry.id)
            .join(ConsumptionMeal)
            .where(
                ConsumptionMeal.consumption_day_id == ConsumptionDay.id,
                ConsumptionEntry.entry_type == "manual_unresolved",
            )
        )
        filters.append(unresolved if has_unresolved_entries else ~unresolved)
    total = session.scalar(select(func.count()).select_from(ConsumptionDay).where(*filters)) or 0
    ordering = (
        ConsumptionDay.consumption_date.asc()
        if sort == "date_asc"
        else ConsumptionDay.updated_at.desc()
        if sort == "updated_at_desc"
        else ConsumptionDay.consumption_date.desc()
    )
    items = list(
        session.scalars(
            select(ConsumptionDay)
            .where(*filters)
            .options(selectinload(ConsumptionDay.meals).selectinload(ConsumptionMeal.entries))
            .order_by(ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, int(total)
