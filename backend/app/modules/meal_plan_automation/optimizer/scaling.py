from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

MAX_COEFFICIENT = 10**15
SCALES = {
    "energy_kcal": Decimal("1"),
    "macro_g": Decimal("1000"),
    "micro_g": Decimal("1000000"),
    "quantity": Decimal("1000"),
    "score": Decimal("10000"),
    "ratio": Decimal("10000"),
}


class ScalingError(ValueError):
    pass


def scale(
    value: Decimal,
    kind: str,
    *,
    bound: str = "nearest",
    allow_negative: bool = False,
) -> int:
    if kind not in SCALES:
        raise ScalingError(f"unknown scale: {kind}")
    if value < 0 and not allow_negative:
        raise ScalingError("negative value")
    rounding = {
        "nearest": ROUND_HALF_UP,
        "lower": ROUND_CEILING,
        "upper": ROUND_FLOOR,
    }.get(bound)
    if rounding is None:
        raise ScalingError("unknown bound")
    result = int((value * SCALES[kind]).to_integral_value(rounding=rounding))
    if abs(result) > MAX_COEFFICIENT:
        raise OverflowError("optimizer integer coefficient overflow")
    return result


def unscale(value: int, kind: str) -> Decimal:
    if kind not in SCALES:
        raise ScalingError(f"unknown scale: {kind}")
    return Decimal(value) / SCALES[kind]
