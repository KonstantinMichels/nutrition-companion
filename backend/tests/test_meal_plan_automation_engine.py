from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.meal_plan_automation.engine import (
    Candidate,
    Component,
    portion_options,
    rank,
    target_fit,
    weighted_score,
)


def test_decimal_portions_and_invalid_ranges():
    assert portion_options(Decimal("0.5"), Decimal("1.5"), Decimal("0.25")) == (
        Decimal("0.5"),
        Decimal("0.75"),
        Decimal("1.00"),
        Decimal("1.25"),
        Decimal("1.50"),
    )
    with pytest.raises(ValueError):
        portion_options(Decimal("0.5"), Decimal("1.6"), Decimal("0.25"))


def test_weighted_score_skips_unavailable_and_target_kinds_are_bounded():
    components = (Component("fit", Decimal("0.8"), "fit"), Component("missing", None, "unknown"))
    assert weighted_score(components, {"fit": Decimal(2), "missing": Decimal(9)}) == Decimal("0.8")
    assert target_fit("range", Decimal(100), Decimal(90), None, Decimal(110)) == 1
    assert target_fit("minimum", Decimal(50), None, Decimal(100), None) == Decimal("0.5")
    assert target_fit("maximum", Decimal(120), None, Decimal(100), None) == Decimal("0.8")


def test_ranking_is_deterministic_with_uuid_tie_breaker():
    component = (Component("fit", Decimal("0.5"), "neutral"),)
    first = Candidate(UUID(int=2), "Rezept", Decimal(1), component)
    second = Candidate(UUID(int=1), "Rezept", Decimal(1), component)
    assert [row[0].recipe_id for row in rank([first, second], {"fit": Decimal(1)})] == [
        UUID(int=1),
        UUID(int=2),
    ]
