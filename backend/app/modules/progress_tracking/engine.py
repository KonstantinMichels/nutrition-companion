from __future__ import annotations

# mypy: disable-error-code="type-arg"
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal, localcontext
from itertools import pairwise
from statistics import median

STABLE_KG_PER_WEEK = Decimal("0.025")
RULE_VERSION = "progress-trend-rules-1.0"


@dataclass(frozen=True, slots=True)
class WeightPoint:
    id: str
    day: date
    value: Decimal
    observed_time: time | None = None
    created_order: int = 0


def representatives(points: Iterable[WeightPoint]) -> list[WeightPoint]:
    chosen: dict[date, WeightPoint] = {}
    for point in points:
        old = chosen.get(point.day)
        point_seconds = (
            point.observed_time.hour * 3600
            + point.observed_time.minute * 60
            + point.observed_time.second
            if point.observed_time
            else -1
        )
        old_key = (
            (
                old.observed_time is not None,
                old.observed_time.hour * 3600
                + old.observed_time.minute * 60
                + old.observed_time.second
                if old.observed_time
                else -1,
                old.created_order,
            )
            if old
            else None
        )
        point_key = (point.observed_time is not None, point_seconds, point.created_order)
        if old_key is None or point_key > old_key:
            chosen[point.day] = point
    return [chosen[key] for key in sorted(chosen)]


def rolling(points: list[WeightPoint], window: int) -> list[dict]:
    result = []
    for point in points:
        start = point.day - timedelta(days=window - 1)
        current = [p for p in points if start <= p.day <= point.day]
        span = (current[-1].day - current[0].day).days if current else 0
        if len(current) < 2 or span < 1:
            average = None
        else:
            average = sum((p.value for p in current), Decimal(0)) / Decimal(len(current))
        density = "low" if len(current) < 3 else "moderate" if len(current) < 5 else "high"
        result.append(
            {
                "date": point.day,
                "value_kg": average,
                "observation_count": len(current),
                "calendar_span_days": span,
                "data_density": density,
            }
        )
    return result


def linear_trend(points: list[WeightPoint]) -> dict:
    if len(points) < 3 or (points[-1].day - points[0].day).days < 7:
        return {
            "available": False,
            "direction": "unavailable",
            "quality_level": "insufficient",
            "observation_count": len(points),
            "covered_days": (points[-1].day - points[0].day).days if points else 0,
        }
    origin = points[0].day
    xs = [Decimal((p.day - origin).days) for p in points]
    ys = [p.value for p in points]
    xbar, ybar = sum(xs) / Decimal(len(xs)), sum(ys) / Decimal(len(ys))
    denominator = sum(((x - xbar) ** 2 for x in xs), Decimal(0))
    slope = (
        sum(((x - xbar) * (y - ybar) for x, y in zip(xs, ys, strict=True)), Decimal(0))
        / denominator
    )
    weekly = slope * Decimal(7)
    # OLS uncertainty is exposed for downstream calibration. 1.96 is a
    # deliberately documented normal approximation; no causal claim is made.
    residual_sum = sum(
        ((y - (ybar + slope * (x - xbar))) ** 2 for x, y in zip(xs, ys, strict=True)),
        Decimal(0),
    )
    with localcontext() as context:
        context.prec = 28
        slope_se = (
            (residual_sum / Decimal(len(points) - 2) / denominator).sqrt()
            if len(points) > 2 and denominator > 0
            else None
        )
    bound = slope_se * Decimal("1.96") if slope_se is not None else None
    covered = int(xs[-1])
    quality = (
        "limited"
        if len(points) < 5 or covered < 14
        else "usable"
        if len(points) < 12 or covered < 42
        else "strong_coverage"
    )
    direction = (
        "stable"
        if abs(weekly) < STABLE_KG_PER_WEEK
        else "increasing"
        if weekly > 0
        else "decreasing"
    )
    return {
        "available": True,
        "direction": direction,
        "kg_per_day": slope,
        "kg_per_week": weekly,
        "slope_standard_error_kg_per_day": slope_se,
        "slope_lower_95_kg_per_day": slope - bound if bound is not None else None,
        "slope_upper_95_kg_per_day": slope + bound if bound is not None else None,
        "quality_level": quality,
        "observation_count": len(points),
        "covered_days": covered,
    }


def interval_changes(points: list[WeightPoint], end: date) -> list[dict]:
    if not points:
        return []
    latest = max((p for p in points if p.day <= end), key=lambda p: p.day, default=None)
    result = []
    for days in (7, 14, 30, 90):
        target = end - timedelta(days=days)
        tolerance = 3 if days <= 14 else 7
        starts = (
            [p for p in points if abs((p.day - target).days) <= tolerance and p.day <= latest.day]
            if latest
            else []
        )
        start = min(starts, key=lambda p: (abs((p.day - target).days), p.day)) if starts else None
        result.append(
            {
                "interval_days": days,
                "change_kg": latest.value - start.value if latest and start else None,
                "start_date": start.day if start else None,
                "end_date": latest.day if latest else None,
            }
        )
    return result


def frequency(points: list[WeightPoint], end: date) -> dict:
    gaps = [(b.day - a.day).days for a, b in pairwise(points)]
    return {
        "observations_last_7_days": sum(p.day >= end - timedelta(days=6) for p in points),
        "observations_last_30_days": sum(p.day >= end - timedelta(days=29) for p in points),
        "median_days_between": str(median(gaps)) if gaps else None,
        "longest_gap_days": max(gaps, default=None),
        "first_observation_date": points[0].day if points else None,
        "latest_observation_date": points[-1].day if points else None,
    }
