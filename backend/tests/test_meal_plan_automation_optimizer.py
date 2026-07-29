from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.meal_plan_automation.optimizer.scaling import ScalingError, scale, unscale
from app.modules.meal_plan_automation.optimizer.solver import (
    ORTOOLS_VERSION,
    RANDOM_SEED,
    SEARCH_WORKERS,
    CpSatMealPlanSolver,
    NutritionBounds,
    OptimizerInput,
    OptimizerOption,
    OptimizerSlot,
)


def option(
    slot: str,
    recipe: int,
    *,
    energy: str,
    score: str,
    day: date = date(2026, 8, 3),
    locked: bool = False,
) -> OptimizerOption:
    recipe_id = UUID(int=recipe)
    return OptimizerOption(
        option_id=f"{slot}-{recipe}-{energy}",
        slot_key=slot,
        day=day,
        recipe_id=recipe_id,
        portion=Decimal(1),
        nutrients={"energy_kcal": Decimal(energy), "protein": Decimal(20)},
        food_requirements={UUID(int=100 + recipe): Decimal(100)},
        preparation_minutes=15,
        suitability=Decimal(score),
        pantry_coverage=Decimal(1),
        data_quality=Decimal(1),
        locked=locked,
    )


def test_solver_dependency_settings_and_scaling_are_explicit():
    assert ORTOOLS_VERSION == "9.14.6206"
    assert SEARCH_WORKERS == 1
    assert RANDOM_SEED == 0
    assert scale(Decimal("12.3456"), "macro_g") == 12346
    assert unscale(12346, "macro_g") == Decimal("12.346")
    assert scale(Decimal("12.1"), "energy_kcal", bound="lower") == 13
    assert scale(Decimal("12.9"), "energy_kcal", bound="upper") == 12
    with pytest.raises(ScalingError):
        scale(Decimal(-1), "quantity")
    with pytest.raises(OverflowError):
        scale(Decimal("10000000000000000"), "micro_g")


def test_joint_solver_fills_every_slot_and_respects_repetition_and_lock():
    source = OptimizerInput(
        slots=(
            OptimizerSlot("breakfast", date(2026, 8, 3)),
            OptimizerSlot("dinner", date(2026, 8, 3)),
        ),
        options=(
            option("breakfast", 1, energy="400", score="0.9", locked=True),
            option("breakfast", 2, energy="500", score="0.8"),
            option("dinner", 1, energy="600", score="0.9"),
            option("dinner", 2, energy="700", score="0.7"),
        ),
        nutrition_by_day={date(2026, 8, 3): NutritionBounds()},
        maximum_repetitions_week=1,
        maximum_repetitions_day=1,
    )
    result = CpSatMealPlanSolver().solve(source)
    assert result.status == "optimal"
    assert set(result.selected_option_ids) == {"breakfast-1-400", "dinner-2-700"}
    assert result.candidate_variable_count == 4


def test_strict_nutrition_and_pantry_can_make_model_infeasible_without_mutation():
    item = option("breakfast", 1, energy="400", score="1")
    pantry: dict[UUID, Decimal] = {}
    source = OptimizerInput(
        slots=(OptimizerSlot("breakfast", item.day),),
        options=(item,),
        nutrition_by_day={
            item.day: NutritionBounds(energy_min=Decimal(800), energy_max=Decimal(900))
        },
        pantry=pantry,
        strict_energy=True,
        strict_pantry=True,
    )
    assert CpSatMealPlanSolver().solve(source).status == "infeasible"
    assert pantry == {}


def test_optional_slot_may_be_skipped():
    source = OptimizerInput(
        slots=(OptimizerSlot("snack", date(2026, 8, 3), required=False),),
        options=(),
        nutrition_by_day={},
        allow_optional_skip=True,
    )
    result = CpSatMealPlanSolver().solve(source)
    assert result.status == "optimal"
    assert result.selected_option_ids == ()
