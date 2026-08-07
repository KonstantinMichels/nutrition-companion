from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.pantry_consumption_reconciliation.engine import (
    LotCandidate,
    reconciliation_status,
    remaining,
    suggest,
)


def _lot(value: int, quantity: str, status: str, relevant: date | None) -> LotCandidate:
    return LotCandidate(
        UUID(int=value),
        Decimal(quantity),
        "g",
        status,
        relevant,
        datetime(2026, 7, value, tzinfo=UTC),
    )


def test_remaining_never_over_reconciles():
    assert remaining(Decimal("250"), Decimal("100")) == Decimal("150")
    assert remaining(Decimal("250"), Decimal("300")) == 0


def test_lot_suggestion_is_deterministic_and_never_silently_uses_past_use_by():
    lots = [
        _lot(5, "500", "past_use_by", date(2026, 7, 20)),
        _lot(3, "100", "no_date", None),
        _lot(2, "200", "expiring_soon", date(2026, 8, 1)),
        _lot(1, "150", "valid", date(2026, 8, 10)),
    ]
    allocations, uncovered = suggest(Decimal("400"), lots)
    assert allocations == [
        (UUID(int=1), Decimal("150")),
        (UUID(int=2), Decimal("200")),
        (UUID(int=3), Decimal("50")),
    ]
    assert uncovered == 0


def test_status_distinguishes_decisions_partial_and_reversal():
    assert (
        reconciliation_status(Decimal("100"), Decimal(0), Decimal(0), {"not_from_pantry"})
        == "not_from_pantry"
    )
    assert (
        reconciliation_status(Decimal("100"), Decimal("40"), Decimal(0), set())
        == "partially_reconciled"
    )
    assert reconciliation_status(Decimal("100"), Decimal(0), Decimal("100"), set()) == "reversed"
