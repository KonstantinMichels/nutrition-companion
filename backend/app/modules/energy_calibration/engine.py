from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.modules.progress_tracking.engine import WeightPoint, linear_trend

from . import rules


@dataclass(frozen=True, slots=True)
class WindowEvaluation:
    eligible: bool
    blockers: tuple[str, ...]
    evidence: dict[str, object]


def evaluate_window(points: list[WeightPoint], start: date, end: date) -> WindowEvaluation:
    selected = [point for point in points if start <= point.day <= end]
    span = (end - start).days + 1
    thirds = max(1, span // 3)
    first_end = start.fromordinal(start.toordinal() + thirds - 1)
    last_start = end.fromordinal(end.toordinal() - thirds + 1)
    weeks = {(point.day.isocalendar().year, point.day.isocalendar().week) for point in selected}
    first_count = sum(point.day <= first_end for point in selected)
    last_count = sum(point.day >= last_start for point in selected)
    trend = linear_trend(selected)
    blockers: list[str] = []
    if not rules.MIN_WINDOW_DAYS <= span <= rules.MAX_WINDOW_DAYS:
        blockers.append("WINDOW_LENGTH")
    if len(selected) < rules.MIN_REPRESENTATIVE_DAYS:
        blockers.append("REPRESENTATIVE_DAYS")
    if len(weeks) < rules.MIN_WEEKS:
        blockers.append("DISTINCT_WEEKS")
    if first_count < rules.MIN_EDGE_POINTS or last_count < rules.MIN_EDGE_POINTS:
        blockers.append("EDGE_COVERAGE")
    if trend.get("quality_level") not in {"usable", "strong_coverage"}:
        blockers.append("TREND_QUALITY")
    return WindowEvaluation(
        not blockers,
        tuple(blockers),
        {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "window_days": span,
            "representative_days": len(selected),
            "distinct_weeks": len(weeks),
            "first_third_days": first_count,
            "last_third_days": last_count,
            "observation_ids": [point.id for point in selected],
            "trend": trend,
        },
    )


def proposal(
    *,
    trend: dict[str, object],
    assumed_intake: Decimal,
    expected_balance: Decimal,
    source_lower: Decimal,
    source_upper: Decimal,
    adherence: str,
    context: str,
) -> dict[str, object]:
    if adherence not in {"high", "moderate"}:
        return {"available": False, "reason": "ADHERENCE_BLOCKED"}
    if context not in {"stable", "minor_changes"}:
        return {"available": False, "reason": "CONTEXT_BLOCKED"}
    slope = Decimal(str(trend["kg_per_day"]))
    low_slope = Decimal(str(trend["slope_lower_95_kg_per_day"]))
    high_slope = Decimal(str(trend["slope_upper_95_kg_per_day"]))
    observed = slope * rules.ENERGY_EQUIVALENT_CENTRAL
    observed_candidates = [
        value * equivalent
        for value in (low_slope, high_slope)
        for equivalent in (rules.ENERGY_EQUIVALENT_LOWER, rules.ENERGY_EQUIVALENT_UPPER)
    ]
    observed_low, observed_high = min(observed_candidates), max(observed_candidates)
    raw = expected_balance - observed
    interval_low, interval_high = expected_balance - observed_high, expected_balance - observed_low
    if interval_low <= 0 <= interval_high:
        return {"available": False, "reason": "UNCERTAINTY_CROSSES_ZERO", "raw_adjustment": raw}
    if abs(raw) < rules.DEADBAND:
        return {"available": False, "reason": "WITHIN_DEADBAND", "raw_adjustment": raw}
    multiplier = (
        rules.REDUCED_CAP_MULTIPLIER
        if adherence == "moderate" or context == "minor_changes"
        else Decimal(1)
    )
    cap = min(rules.ABSOLUTE_CAP, abs(assumed_intake) * rules.RELATIVE_CAP) * multiplier
    adjustment = max(-cap, min(cap, raw))
    return {
        "available": True,
        "reason": None,
        "observed_balance_central_kcal_per_day": observed,
        "observed_balance_lower_kcal_per_day": observed_low,
        "observed_balance_upper_kcal_per_day": observed_high,
        "expected_balance_kcal_per_day": expected_balance,
        "raw_adjustment_kcal_per_day": raw,
        "adjustment_lower_kcal_per_day": interval_low,
        "adjustment_upper_kcal_per_day": interval_high,
        "cap_kcal_per_day": cap,
        "proposed_adjustment_kcal_per_day": adjustment,
        "proposed_target_kcal_per_day": assumed_intake + adjustment,
        "proposed_target_lower_kcal_per_day": source_lower + adjustment,
        "proposed_target_upper_kcal_per_day": source_upper + adjustment,
    }
