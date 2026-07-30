from datetime import date, timedelta
from decimal import Decimal

from app.modules.energy_calibration.engine import evaluate_window, proposal
from app.modules.progress_tracking.engine import WeightPoint


def _points(slope: Decimal = Decimal("-0.01")) -> list[WeightPoint]:
    start = date(2026, 1, 1)
    return [
        WeightPoint(
            str(index),
            start + timedelta(days=index * 3),
            Decimal("80") + slope * Decimal(index * 3),
        )
        for index in range(10)
    ]


def test_dense_window_has_uncertainty_and_is_eligible() -> None:
    points = _points()
    result = evaluate_window(points, points[0].day, points[-1].day)
    assert result.eligible
    trend = result.evidence["trend"]
    assert isinstance(trend, dict)
    assert trend["slope_standard_error_kg_per_day"] is not None


def test_adjustment_is_capped_and_moderate_halves_cap() -> None:
    trend = {
        "kg_per_day": Decimal("-0.05"),
        "slope_lower_95_kg_per_day": Decimal("-0.055"),
        "slope_upper_95_kg_per_day": Decimal("-0.045"),
    }
    result = proposal(
        trend=trend,
        assumed_intake=Decimal("2000"),
        expected_balance=Decimal(0),
        source_lower=Decimal("1900"),
        source_upper=Decimal("2100"),
        adherence="moderate",
        context="stable",
    )
    assert result["available"] is True
    assert result["cap_kcal_per_day"] == Decimal("100")
    assert result["proposed_adjustment_kcal_per_day"] == Decimal("100")


def test_uncertainty_crossing_zero_withholds_proposal() -> None:
    result = proposal(
        trend={
            "kg_per_day": Decimal("0.01"),
            "slope_lower_95_kg_per_day": Decimal("-0.01"),
            "slope_upper_95_kg_per_day": Decimal("0.02"),
        },
        assumed_intake=Decimal("2000"),
        expected_balance=Decimal(0),
        source_lower=Decimal("1900"),
        source_upper=Decimal("2100"),
        adherence="high",
        context="stable",
    )
    assert result["available"] is False
    assert result["reason"] == "UNCERTAINTY_CROSSES_ZERO"
