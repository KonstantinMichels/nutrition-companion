from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class Component:
    code: str
    score: Decimal | None
    explanation_de: str


@dataclass(frozen=True)
class Candidate:
    recipe_id: UUID
    recipe_name: str
    portion: Decimal
    components: tuple[Component, ...]
    exclusions: tuple[str, ...] = ()
    warning_count: int = 0
    preparation_minutes: int | None = None


def portion_options(
    minimum: Decimal, maximum: Decimal, step: Decimal, limit: int = 25
) -> tuple[Decimal, ...]:
    if minimum <= 0 or maximum < minimum or step <= 0:
        raise ValueError("invalid portion range")
    count = int(((maximum - minimum) / step).to_integral_value()) + 1
    if minimum + step * (count - 1) != maximum or count > limit:
        raise ValueError("invalid portion step")
    return tuple(minimum + step * index for index in range(count))


def weighted_score(
    components: tuple[Component, ...], weights: Mapping[str, Decimal]
) -> Decimal | None:
    numerator = denominator = Decimal(0)
    for component in components:
        weight = weights.get(component.code, Decimal(0))
        if weight < 0 or weight > 10:
            raise ValueError("invalid weight")
        if component.score is None or weight == 0:
            continue
        if not Decimal(0) <= component.score <= Decimal(1):
            raise ValueError("invalid component score")
        numerator += component.score * weight
        denominator += weight
    return None if denominator == 0 else numerator / denominator


def target_fit(
    kind: str, projected: Decimal, low: Decimal | None, value: Decimal | None, high: Decimal | None
) -> Decimal | None:
    if kind == "range" and low is not None and high is not None:
        if low <= projected <= high:
            return Decimal(1)
        boundary = low if projected < low else high
        return max(Decimal(0), Decimal(1) - abs(projected - boundary) / max(boundary, Decimal(1)))
    if kind == "minimum" and (value or low) is not None:
        target = value or low
        assert target is not None
        return min(projected / target, Decimal(1))
    if kind == "maximum" and (value or high) is not None:
        target = value or high
        assert target is not None
        return (
            Decimal(1)
            if projected <= target
            else max(Decimal(0), Decimal(1) - (projected - target) / max(target, Decimal(1)))
        )
    if kind == "reference" and value is not None:
        return max(Decimal(0), Decimal(1) - abs(projected - value) / max(value, Decimal(1)))
    return None


def rank(
    candidates: list[Candidate], weights: Mapping[str, Decimal]
) -> list[tuple[Candidate, Decimal | None]]:
    rows = [(candidate, weighted_score(candidate.components, weights)) for candidate in candidates]
    return sorted(
        rows,
        key=lambda row: (
            bool(row[0].exclusions),
            -(row[1] or Decimal(-1)),
            row[0].warning_count,
            row[0].preparation_minutes if row[0].preparation_minutes is not None else 10**9,
            row[0].recipe_name.casefold(),
            str(row[0].recipe_id),
            row[0].portion,
        ),
    )
