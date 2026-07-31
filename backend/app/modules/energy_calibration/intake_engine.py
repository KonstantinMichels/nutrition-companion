"""Pure, deterministic intake-informed calibration calculations."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, getcontext
from typing import Any

from . import rules

getcontext().prec = 28

# Two-sided 95% Student-t critical values; df > 30 uses stable asymptotic values.
_T95 = (
    0,
    Decimal("12.706"),
    Decimal("4.303"),
    Decimal("3.182"),
    Decimal("2.776"),
    Decimal("2.571"),
    Decimal("2.447"),
    Decimal("2.365"),
    Decimal("2.306"),
    Decimal("2.262"),
    Decimal("2.228"),
    Decimal("2.201"),
    Decimal("2.179"),
    Decimal("2.160"),
    Decimal("2.145"),
    Decimal("2.131"),
    Decimal("2.120"),
    Decimal("2.110"),
    Decimal("2.101"),
    Decimal("2.093"),
    Decimal("2.086"),
    Decimal("2.080"),
    Decimal("2.074"),
    Decimal("2.069"),
    Decimal("2.064"),
    Decimal("2.060"),
    Decimal("2.056"),
    Decimal("2.052"),
    Decimal("2.048"),
    Decimal("2.045"),
    Decimal("2.042"),
)


def _sqrt(value: Decimal) -> Decimal:
    return value.sqrt() if value > 0 else Decimal(0)


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def intake_summary(values: list[Decimal], confidence: str, routine: str) -> dict[str, object]:
    count = len(values)
    mean = sum(values, Decimal(0)) / Decimal(count)
    median = _median(values)
    variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / Decimal(count - 1)
    deviation = _sqrt(variance)
    sem = deviation / _sqrt(Decimal(count))
    df = count - 1
    critical = _T95[df] if df <= 30 else Decimal("2.000") if df <= 60 else Decimal("1.960")
    statistical_lower = max(Decimal(0), mean - critical * sem)
    statistical_upper = mean + critical * sem
    allowance_rate = (
        rules.HIGH_REPORTING_ALLOWANCE
        if confidence == "high"
        else rules.MODERATE_REPORTING_ALLOWANCE
    )
    if routine == "minor_changes":
        allowance_rate += rules.MINOR_ROUTINE_ALLOWANCE
    allowance = mean * allowance_rate
    # Descriptive only: Tukey's 1.5 IQR fences. Values are never excluded automatically.
    ordered = sorted(values)
    lower_half, upper_half = ordered[: count // 2], ordered[(count + 1) // 2 :]
    q1, q3 = _median(lower_half), _median(upper_half)
    iqr = q3 - q1
    return {
        "usable_day_count": count,
        "mean_recorded_intake_kcal": mean,
        "median_recorded_intake_kcal": median,
        "minimum_recorded_intake_kcal": min(values),
        "maximum_recorded_intake_kcal": max(values),
        "standard_deviation_kcal": deviation,
        "standard_error_of_mean_kcal": sem,
        "statistical_lower_kcal": statistical_lower,
        "statistical_upper_kcal": statistical_upper,
        "t_critical_95": critical,
        "degrees_of_freedom": df,
        "reporting_allowance_rate": allowance_rate,
        "reporting_allowance_kcal": allowance,
        "final_lower_kcal": max(Decimal(0), statistical_lower - allowance),
        "final_upper_kcal": statistical_upper + allowance,
        "unusual_lower_fence_kcal": q1 - Decimal("1.5") * iqr,
        "unusual_upper_fence_kcal": q3 + Decimal("1.5") * iqr,
    }


def coverage(
    days: list[date], start: date, end: date
) -> tuple[dict[str, object], list[dict[str, object]]]:
    span = (end - start).days + 1
    unique = sorted(set(days))
    thirds = max(1, span // 3)
    first_end, last_start = start + timedelta(days=thirds - 1), end - timedelta(days=thirds - 1)
    gaps: list[int] = []
    cursor = start
    for day in unique:
        gaps.append((day - cursor).days)
        cursor = day + timedelta(days=1)
    gaps.append((end - cursor).days + 1)
    values: dict[str, Any] = {
        "calendar_day_count": span,
        "coverage_ratio": Decimal(len(unique)) / Decimal(span),
        "distinct_weeks": len({(d.isocalendar().year, d.isocalendar().week) for d in unique}),
        "first_third_days": sum(d <= first_end for d in unique),
        "final_third_days": sum(d >= last_start for d in unique),
        "maximum_gap_days": max(gaps, default=span),
        "weekday_days": sum(d.weekday() < 5 for d in unique),
        "weekend_days": sum(d.weekday() >= 5 for d in unique),
    }
    specs = [
        (
            "minimum_usable_intake_days_met",
            len(unique) >= rules.MIN_INTAKE_DAYS,
            len(unique),
            rules.MIN_INTAKE_DAYS,
            "Mindestens 14 nutzbare Verzehrtage.",
        ),
        (
            "usable_intake_ratio_met",
            values["coverage_ratio"] >= rules.MIN_INTAKE_COVERAGE,
            values["coverage_ratio"],
            rules.MIN_INTAKE_COVERAGE,
            "Mindestens 70 % der Kalendertage müssen nutzbar sein.",
        ),
        (
            "minimum_intake_weeks_met",
            values["distinct_weeks"] >= rules.MIN_INTAKE_WEEKS,
            values["distinct_weeks"],
            rules.MIN_INTAKE_WEEKS,
            "Nutzbare Tage müssen mindestens drei Kalenderwochen abdecken.",
        ),
        (
            "first_third_intake_coverage_met",
            values["first_third_days"] >= rules.MIN_INTAKE_EDGE_DAYS,
            values["first_third_days"],
            rules.MIN_INTAKE_EDGE_DAYS,
            "Im ersten Drittel fehlen nutzbare Tage.",
        ),
        (
            "final_third_intake_coverage_met",
            values["final_third_days"] >= rules.MIN_INTAKE_EDGE_DAYS,
            values["final_third_days"],
            rules.MIN_INTAKE_EDGE_DAYS,
            "Im letzten Drittel fehlen nutzbare Tage.",
        ),
        (
            "maximum_intake_gap_met",
            values["maximum_gap_days"] <= rules.MAX_INTAKE_GAP_DAYS,
            values["maximum_gap_days"],
            rules.MAX_INTAKE_GAP_DAYS,
            "Eine Aufzeichnungslücke ist länger als vier Tage.",
        ),
    ]
    if span >= 28:
        specs += [
            (
                "weekday_coverage_met",
                values["weekday_days"] >= rules.MIN_WEEKDAY_DAYS,
                values["weekday_days"],
                rules.MIN_WEEKDAY_DAYS,
                "Es fehlen nutzbare Wochentage.",
            ),
            (
                "weekend_coverage_met",
                values["weekend_days"] >= rules.MIN_WEEKEND_DAYS,
                values["weekend_days"],
                rules.MIN_WEEKEND_DAYS,
                "Es fehlen nutzbare Wochenendtage.",
            ),
        ]
    checks = [
        {
            "code": code,
            "passed": passed,
            "current": current,
            "required": required,
            "explanation_de": explanation,
        }
        for code, passed, current, required, explanation in specs
    ]
    return values, checks


def calculate(
    *,
    intake: dict[str, object],
    trend: dict[str, object],
    source_tdee: Decimal,
    source_goal_adjustment: Decimal,
    source_lower: Decimal,
    source_upper: Decimal,
    confidence: str,
    routine: str,
) -> tuple[dict[str, object], dict[str, object] | None]:
    slope = Decimal(str(trend["kg_per_day"]))
    slope_low = Decimal(str(trend["slope_lower_95_kg_per_day"]))
    slope_high = Decimal(str(trend["slope_upper_95_kg_per_day"]))
    balance_values = [
        value * equivalent
        for value in (slope_low, slope_high)
        for equivalent in (rules.ENERGY_EQUIVALENT_LOWER, rules.ENERGY_EQUIVALENT_UPPER)
    ]
    balance, balance_low, balance_high = (
        slope * rules.ENERGY_EQUIVALENT_CENTRAL,
        min(balance_values),
        max(balance_values),
    )
    mean = Decimal(str(intake["mean_recorded_intake_kcal"]))
    intake_low, intake_high = (
        Decimal(str(intake["final_lower_kcal"])),
        Decimal(str(intake["final_upper_kcal"])),
    )
    tdees = [i - b for i in (intake_low, intake_high) for b in (balance_low, balance_high)]
    tdee, tdee_low, tdee_high = mean - balance, min(tdees), max(tdees)
    raw, adjust_low, adjust_high = (
        tdee - source_tdee,
        tdee_low - source_tdee,
        tdee_high - source_tdee,
    )
    direction_uncertain = adjust_low <= 0 <= adjust_high
    calc: dict[str, object] = {
        "sign_convention": "energy_balance = recorded_intake - estimated_expenditure",
        "observed_balance_central_kcal": balance,
        "observed_balance_lower_kcal": balance_low,
        "observed_balance_upper_kcal": balance_high,
        "estimated_tdee_central_kcal": tdee,
        "estimated_tdee_lower_kcal": tdee_low,
        "estimated_tdee_upper_kcal": tdee_high,
        "source_tdee_kcal": source_tdee,
        "source_goal_adjustment_kcal": source_goal_adjustment,
        "unbounded_baseline_adjustment_kcal": raw,
        "adjustment_lower_kcal": adjust_low,
        "adjustment_upper_kcal": adjust_high,
        "direction": "uncertain" if direction_uncertain else "higher" if raw > 0 else "lower",
    }
    if direction_uncertain or abs(raw) < rules.INTAKE_DEADBAND:
        calc["result"] = "direction_uncertain" if direction_uncertain else "no_meaningful_change"
        return calc, None
    multiplier = Decimal(1)
    cap_reasons: list[str] = []
    if confidence == "moderate":
        multiplier *= Decimal("0.5")
        cap_reasons.append("moderate_recording_confidence")
    if routine == "minor_changes":
        multiplier *= Decimal("0.5")
        cap_reasons.append("minor_routine_changes")
    cap = min(rules.INTAKE_ABSOLUTE_CAP, abs(source_tdee) * rules.INTAKE_RELATIVE_CAP) * multiplier
    adjustment = max(-cap, min(cap, raw))
    proposal = {
        "available": True,
        "unbounded_baseline_adjustment_kcal": raw,
        "effective_cap_kcal": cap,
        "cap_reasons": cap_reasons,
        "proposed_adjustment_kcal_per_day": adjustment,
        "proposed_baseline_adjustment_kcal": adjustment,
        "proposed_estimated_tdee_kcal": source_tdee + adjustment,
        "source_goal_adjustment_kcal": source_goal_adjustment,
        "proposed_target_kcal_per_day": source_tdee + adjustment + source_goal_adjustment,
        "proposed_target_lower_kcal_per_day": source_lower + adjustment,
        "proposed_target_upper_kcal_per_day": source_upper + adjustment,
        "capped": abs(raw) > cap,
    }
    calc["result"] = "proposal_available"
    return calc, proposal
