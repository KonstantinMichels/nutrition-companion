"""Decimal helpers used by the deterministic nutrition engine.

All public calculations operate on :class:`~decimal.Decimal`.  Converting via
``str`` avoids importing the binary approximation of a JSON float, and display
rounding is deliberately isolated in this module.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

type DecimalLike = Decimal | int | float | str


class NumericInputError(ValueError):
    """Raised when a calculation receives a malformed or non-finite number."""


def as_decimal(value: DecimalLike, *, field: str = "value") -> Decimal:
    """Return a finite decimal without rounding it."""

    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise NumericInputError(f"{field} must be a valid decimal") from exc
    if not result.is_finite():
        raise NumericInputError(f"{field} must be finite")
    return result


def format_decimal_de(value: Decimal, decimal_places: int) -> str:
    """Round only for display and format with a German decimal separator."""

    if decimal_places < 0:
        raise ValueError("decimal_places must not be negative")
    quantum = Decimal(1).scaleb(-decimal_places)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    rendered = f"{rounded:.{decimal_places}f}"
    return rendered.replace(".", ",")
