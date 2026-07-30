from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from . import rules


@dataclass(frozen=True, slots=True)
class SessionInput:
    id: str
    day: date
    duration_minutes: int
    intensity: str
    session_type: str
    baseline_inclusion: str
    version: int


def classify(sessions: list[SessionInput]) -> dict[str, object]:
    if not sessions:
        return {"category": "rest", "points": Decimal(0), "rule_version": rules.RULE_VERSION}
    points = sum(
        (Decimal(item.duration_minutes) / Decimal(60))
        * rules.INTENSITY_FACTORS[item.intensity]
        * rules.TYPE_FACTORS[item.session_type]
        for item in sessions
    )
    points = min(points, Decimal("12"))
    inclusions = {item.baseline_inclusion for item in sessions}
    uncertain = "unknown" in inclusions or len(inclusions) > 1
    recovery_only = all(item.session_type == "recovery" for item in sessions)
    category = (
        "mixed_uncertain"
        if uncertain
        else "recovery"
        if recovery_only
        else "light"
        if points < Decimal("0.75")
        else "moderate"
        if points < Decimal("1.5")
        else "high"
        if points < Decimal("2.75")
        else "very_high"
    )
    return {"category": category, "points": points, "rule_version": rules.RULE_VERSION}


def effective_cap(baseline: Decimal, absolute: Decimal, relative: Decimal) -> Decimal:
    return min(
        absolute, rules.RULE_POSITIVE_CAP, baseline * relative, baseline * rules.RULE_RELATIVE_CAP
    )


def additive(
    category: str,
    baseline: Decimal,
    sessions: list[SessionInput],
    absolute_cap: Decimal,
    relative_cap: Decimal,
    selected: Decimal | None,
) -> dict[str, object]:
    inclusions = {item.baseline_inclusion for item in sessions}
    cap = effective_cap(baseline, absolute_cap, relative_cap)
    allowed = inclusions <= {"additional_to_baseline", "partially_included"} and bool(sessions)
    low, high = rules.ADDITIVE_RANGES[category] if allowed else (Decimal(0), Decimal(0))
    if "partially_included" in inclusions:
        low, high = low / 2, high / 2
    low, high = min(low, cap), min(high, cap)
    chosen = (low + high) / 2 if selected is None else selected
    if chosen < 0 or chosen > cap or (chosen != 0 and not allowed):
        raise ValueError("selected energy delta outside allowed bounds")
    return {
        "suggested_min": low,
        "suggested_max": high,
        "selected": chosen,
        "cap": cap,
        "allowed": allowed,
        "unbounded_max": rules.ADDITIVE_RANGES[category][1],
    }


def redistribute(
    days: list[tuple[date, str]],
    baseline: Decimal,
    positive_cap: Decimal,
    negative_cap: Decimal,
    relative_cap: Decimal,
    floor: Decimal,
    strength: Decimal,
) -> list[dict[str, object]]:
    raw = [Decimal(1) + (rules.WEIGHTS[category] - Decimal(1)) * strength for _, category in days]
    mean = sum(raw, Decimal(0)) / Decimal(7)
    pos = effective_cap(baseline, positive_cap, relative_cap)
    neg = min(
        negative_cap,
        rules.RULE_NEGATIVE_CAP,
        baseline * relative_cap,
        baseline * rules.RULE_RELATIVE_CAP,
    )
    deltas = [max(-neg, min(pos, baseline * weight / mean - baseline)) for weight in raw]
    minimum = max(floor, baseline * rules.MINIMUM_RELATIVE_TARGET)
    lower = max(-neg, minimum - baseline)
    deltas = [max(delta, lower) for delta in deltas]
    difference = -sum(deltas, Decimal(0))
    for _ in range(20):
        if abs(difference) < Decimal("0.0001"):
            break
        candidates = [
            i
            for i, delta in enumerate(deltas)
            if (difference > 0 and delta < pos) or (difference < 0 and delta > lower)
        ]
        if not candidates:
            raise ValueError("redistribution infeasible")
        share = difference / Decimal(len(candidates))
        for index in candidates:
            updated = max(lower, min(pos, deltas[index] + share))
            difference -= updated - deltas[index]
            deltas[index] = updated
    if abs(sum(deltas, Decimal(0))) >= Decimal("0.01"):
        raise ValueError("redistribution infeasible")
    return [
        {
            "date": day.isoformat(),
            "category": category,
            "weight": weight,
            "delta": delta,
            "adjusted": baseline + delta,
        }
        for (day, category), weight, delta in zip(days, raw, deltas, strict=True)
    ]
