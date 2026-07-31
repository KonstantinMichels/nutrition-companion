from datetime import date, timedelta
from decimal import Decimal

from app.modules.energy_calibration import intake_engine


def test_intake_statistics_preserve_values_and_widen_reporting_interval():
    values = [Decimal(2200 + (index % 5) * 50) for index in range(21)]
    high = intake_engine.intake_summary(values, "high", "representative")
    moderate = intake_engine.intake_summary(values, "moderate", "minor_changes")

    assert high["mean_recorded_intake_kcal"] == sum(values) / Decimal(21)
    assert high["minimum_recorded_intake_kcal"] == min(values)
    assert high["maximum_recorded_intake_kcal"] == max(values)
    assert moderate["reporting_allowance_rate"] == Decimal("0.13")
    assert moderate["final_lower_kcal"] < high["final_lower_kcal"]
    assert moderate["final_upper_kcal"] > high["final_upper_kcal"]


def test_coverage_detects_missing_days_without_imputation():
    start = date(2026, 7, 1)
    days = [start + timedelta(days=index) for index in range(28) if index not in range(10, 16)]
    values, checks = intake_engine.coverage(days, start, start + timedelta(days=27))

    assert values["calendar_day_count"] == 28
    assert values["maximum_gap_days"] == 6
    assert (
        next(item for item in checks if item["code"] == "maximum_intake_gap_met")["passed"] is False
    )


def test_tdee_interval_uses_all_cross_products_and_blocks_uncertain_direction():
    intake = {
        "mean_recorded_intake_kcal": Decimal("2500"),
        "final_lower_kcal": Decimal("2200"),
        "final_upper_kcal": Decimal("2800"),
    }
    trend = {
        "kg_per_day": Decimal("-0.02"),
        "slope_lower_95_kg_per_day": Decimal("-0.04"),
        "slope_upper_95_kg_per_day": Decimal("0.01"),
    }
    calculation, proposal = intake_engine.calculate(
        intake=intake,
        trend=trend,
        source_tdee=Decimal("2700"),
        source_goal_adjustment=Decimal("-300"),
        source_lower=Decimal("2300"),
        source_upper=Decimal("2500"),
        confidence="high",
        routine="representative",
    )

    assert calculation["estimated_tdee_lower_kcal"] == Decimal("2105")
    assert calculation["estimated_tdee_upper_kcal"] == Decimal("3180")
    assert calculation["direction"] == "uncertain"
    assert proposal is None


def test_moderate_and_minor_caps_combine_conservatively():
    intake = {
        "mean_recorded_intake_kcal": Decimal("3200"),
        "final_lower_kcal": Decimal("3150"),
        "final_upper_kcal": Decimal("3250"),
    }
    trend = {
        "kg_per_day": Decimal("0"),
        "slope_lower_95_kg_per_day": Decimal("0"),
        "slope_upper_95_kg_per_day": Decimal("0"),
    }
    _calculation, proposal = intake_engine.calculate(
        intake=intake,
        trend=trend,
        source_tdee=Decimal("2800"),
        source_goal_adjustment=Decimal("-300"),
        source_lower=Decimal("2400"),
        source_upper=Decimal("2600"),
        confidence="moderate",
        routine="minor_changes",
    )

    assert proposal is not None
    assert proposal["effective_cap_kcal"] == Decimal("50.00")
    assert proposal["proposed_baseline_adjustment_kcal"] == Decimal("50.00")
    assert proposal["proposed_target_kcal_per_day"] == Decimal("2550.00")
