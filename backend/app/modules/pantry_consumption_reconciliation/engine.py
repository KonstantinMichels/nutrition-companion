"""Pure Decimal-safe reconciliation calculations; no persistence or inference."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LotCandidate:
    id: UUID
    available: Decimal
    unit: str
    date_status: str
    relevant_date: date | None
    created_at: datetime


def remaining(required: Decimal, active_reconciled: Decimal) -> Decimal:
    return max(Decimal(0), required - active_reconciled)


def lot_sort_key(lot: LotCandidate) -> tuple[object, ...]:
    rank = {
        "valid": 0,
        "date_today": 1,
        "expiring_soon": 2,
        "no_date": 3,
        "past_best_before": 4,
        "past_use_by": 5,
    }.get(lot.date_status, 6)
    # Dates are meaningful before undated/past-date tie breaking; UUID is final deterministic key.
    return rank, lot.relevant_date or date.max, lot.created_at, str(lot.id)


def suggest(
    quantity: Decimal, lots: list[LotCandidate]
) -> tuple[list[tuple[UUID, Decimal]], Decimal]:
    outstanding = quantity
    allocations: list[tuple[UUID, Decimal]] = []
    for lot in sorted(lots, key=lot_sort_key):
        if outstanding <= 0:
            break
        # A past use-by lot is visible but never selected silently.
        if lot.date_status == "past_use_by":
            continue
        allocated = min(outstanding, lot.available)
        if allocated > 0:
            allocations.append((lot.id, allocated))
            outstanding -= allocated
    return allocations, outstanding


def reconciliation_status(
    required: Decimal | None,
    reconciled: Decimal,
    reversed_quantity: Decimal,
    decisions: set[str],
) -> str:
    if reconciled == 0 and reversed_quantity > 0:
        return "reversed"
    if reversed_quantity > 0:
        return "partially_reversed"
    if "not_from_pantry" in decisions:
        return "not_from_pantry"
    if "already_accounted_for" in decisions or "leftovers_already_accounted_for" in decisions:
        return "already_accounted_for"
    if required is None:
        return "unresolved"
    if reconciled <= 0:
        return "not_started"
    return "fully_reconciled" if reconciled >= required else "partially_reconciled"
