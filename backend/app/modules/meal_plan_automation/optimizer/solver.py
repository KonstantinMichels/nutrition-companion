from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from importlib.metadata import version
from typing import Any, Literal
from uuid import UUID

from ortools.sat.python import cp_model

from app.modules.meal_plan_automation.optimizer.scaling import scale

ORTOOLS_VERSION = version("ortools")
RANDOM_SEED = 0
SEARCH_WORKERS = 1


@dataclass(frozen=True)
class OptimizerOption:
    option_id: str
    slot_key: str
    day: date
    recipe_id: UUID
    portion: Decimal
    nutrients: dict[str, Decimal]
    food_requirements: dict[UUID, Decimal]
    preparation_minutes: int | None
    suitability: Decimal
    pantry_coverage: Decimal
    data_quality: Decimal
    manually_selected: bool = False
    locked: bool = False


@dataclass(frozen=True)
class OptimizerSlot:
    key: str
    day: date
    required: bool = True


@dataclass(frozen=True)
class NutritionBounds:
    energy_min: Decimal | None = None
    energy_max: Decimal | None = None
    protein_min: Decimal | None = None
    fiber_min: Decimal | None = None
    fat_min: Decimal | None = None
    fat_max: Decimal | None = None
    saturated_fat_max: Decimal | None = None


@dataclass(frozen=True)
class OptimizerInput:
    slots: tuple[OptimizerSlot, ...]
    options: tuple[OptimizerOption, ...]
    nutrition_by_day: dict[date, NutritionBounds]
    existing_nutrients_by_day: dict[date, dict[str, Decimal]] = field(default_factory=dict)
    existing_recipe_dates: dict[UUID, tuple[date, ...]] = field(default_factory=dict)
    pantry: dict[UUID, Decimal] = field(default_factory=dict)
    shopping_commitments: dict[UUID, Decimal] = field(default_factory=dict)
    maximum_repetitions_week: int = 2
    maximum_repetitions_day: int = 2
    minimum_day_gap: int = 0
    maximum_daily_preparation_minutes: int | None = None
    maximum_unique_shopping_items: int | None = None
    strict_energy: bool = False
    strict_protein: bool = False
    strict_fiber: bool = False
    strict_pantry: bool = False
    allow_optional_skip: bool = False
    objective_weights: dict[str, Decimal] = field(default_factory=dict)
    meal_prep_preference: Literal["neutral", "prefer_reuse", "prefer_variety"] = "neutral"
    time_limit_seconds: Decimal = Decimal("5")
    relative_gap_limit: Decimal = Decimal("0.02")


@dataclass(frozen=True)
class SolverResult:
    status: Literal[
        "optimal",
        "feasible",
        "infeasible",
        "unknown",
        "invalid_model",
        "time_limit_without_solution",
    ]
    selected_option_ids: tuple[str, ...]
    solve_time_seconds: Decimal
    objective_value: Decimal | None
    best_objective_bound: Decimal | None
    relative_gap: Decimal | None
    candidate_variable_count: int
    constraint_count: int
    binding_constraints: tuple[str, ...]


class MealPlanSolver:
    def solve(self, source: OptimizerInput) -> SolverResult:
        raise NotImplementedError


class CpSatMealPlanSolver(MealPlanSolver):
    def solve(self, source: OptimizerInput) -> SolverResult:
        started = time.monotonic()
        model = cp_model.CpModel()
        variables = {
            option.option_id: model.new_bool_var(option.option_id) for option in source.options
        }
        constraints = 0
        by_slot: dict[str, list[OptimizerOption]] = {slot.key: [] for slot in source.slots}
        for option in source.options:
            by_slot.setdefault(option.slot_key, []).append(option)
        for slot in source.slots:
            expression = sum(variables[item.option_id] for item in by_slot.get(slot.key, []))
            if slot.required and not source.allow_optional_skip:
                model.add(expression == 1)
            else:
                model.add(expression <= 1)
            constraints += 1
        for option in source.options:
            if option.locked:
                model.add(variables[option.option_id] == 1)
                constraints += 1

        recipes = sorted({item.recipe_id for item in source.options}, key=str)
        unique_recipe_vars: dict[UUID, cp_model.IntVar] = {}
        for recipe_id in recipes:
            recipe_options = [item for item in source.options if item.recipe_id == recipe_id]
            fixed_dates = source.existing_recipe_dates.get(recipe_id, ())
            unique = model.new_bool_var(f"recipe_used_{recipe_id}")
            unique_recipe_vars[recipe_id] = unique
            selected_recipe = sum(variables[item.option_id] for item in recipe_options)
            model.add(selected_recipe >= unique)
            model.add(selected_recipe <= len(recipe_options) * unique)
            constraints += 2
            model.add(selected_recipe <= max(0, source.maximum_repetitions_week - len(fixed_dates)))
            constraints += 1
            for day in sorted({item.day for item in recipe_options}):
                same_day = [item for item in recipe_options if item.day == day]
                model.add(
                    sum(variables[item.option_id] for item in same_day)
                    <= max(
                        0,
                        source.maximum_repetitions_day
                        - sum(existing_day == day for existing_day in fixed_dates),
                    )
                )
                constraints += 1
            if source.minimum_day_gap:
                for item in recipe_options:
                    if any(
                        0 < abs((item.day - fixed_day).days) <= source.minimum_day_gap
                        for fixed_day in fixed_dates
                    ):
                        model.add(variables[item.option_id] == 0)
                        constraints += 1
                for left in recipe_options:
                    for right in recipe_options:
                        day_gap = abs((left.day - right.day).days)
                        if (
                            left.option_id < right.option_id
                            and 0 < day_gap <= source.minimum_day_gap
                        ):
                            model.add(variables[left.option_id] + variables[right.option_id] <= 1)
                            constraints += 1

        days = sorted({slot.day for slot in source.slots})
        for day in days:
            daily = [item for item in source.options if item.day == day]
            if source.maximum_daily_preparation_minutes is not None:
                known = [item for item in daily if item.preparation_minutes is not None]
                model.add(
                    sum(
                        variables[item.option_id] * int(item.preparation_minutes or 0)
                        for item in known
                    )
                    <= source.maximum_daily_preparation_minutes
                )
                constraints += 1
            bounds = source.nutrition_by_day.get(day, NutritionBounds())
            fixed = source.existing_nutrients_by_day.get(day, {})
            constraints += self._nutrition_constraints(
                model, variables, daily, bounds, fixed, source
            )

        foods = sorted(
            {food for item in source.options for food in item.food_requirements}, key=str
        )
        missing_flags = []
        for food_id in foods:
            requirements = [
                (item, item.food_requirements[food_id])
                for item in source.options
                if food_id in item.food_requirements
            ]
            available = source.pantry.get(food_id, Decimal(0)) + source.shopping_commitments.get(
                food_id, Decimal(0)
            )
            required_expression = sum(
                variables[item.option_id] * scale(quantity, "quantity")
                for item, quantity in requirements
            )
            available_scaled = scale(available, "quantity")
            if source.strict_pantry:
                model.add(required_expression <= available_scaled)
                constraints += 1
            missing = model.new_int_var(0, 10**12, f"missing_{food_id}")
            model.add(missing >= required_expression - available_scaled)
            constraints += 1
            flag = model.new_bool_var(f"missing_flag_{food_id}")
            model.add(missing <= 10**12 * flag)
            model.add(missing >= flag)
            constraints += 2
            missing_flags.append(flag)
        if source.maximum_unique_shopping_items is not None:
            model.add(sum(missing_flags) <= source.maximum_unique_shopping_items)
            constraints += 1

        costs: list[cp_model.LinearExpr] = []
        for order, option in enumerate(sorted(source.options, key=lambda item: item.option_id), 1):
            score_cost = scale(Decimal(1) - option.suitability, "score")
            pantry_cost = scale(Decimal(1) - option.pantry_coverage, "score")
            quality_cost = scale(Decimal(1) - option.data_quality, "score")
            cost = (
                score_cost * int(source.objective_weights.get("nutrition_fit", Decimal(1)) * 10)
                + pantry_cost * int(source.objective_weights.get("pantry_usage", Decimal(1)) * 10)
                + quality_cost * int(source.objective_weights.get("data_quality", Decimal(1)) * 10)
                + int(option.preparation_minutes or 120)
                * int(source.objective_weights.get("preparation_time", Decimal(1)) * 10)
                + order
            )
            costs.append(variables[option.option_id] * cost)
        variety_weight = int(source.objective_weights.get("variety", Decimal(1)) * 100)
        meal_prep_weight = int(source.objective_weights.get("meal_prep", Decimal(1)) * 100)
        unique_count = sum(unique_recipe_vars.values())
        unique_cost = (
            unique_count * meal_prep_weight if source.meal_prep_preference == "prefer_reuse" else 0
        )
        repetition_cost = (len(source.slots) - unique_count) * (
            variety_weight
            + (meal_prep_weight if source.meal_prep_preference == "prefer_variety" else 0)
        )
        shopping_weight = int(source.objective_weights.get("shopping_effort", Decimal(1)) * 10000)
        model.minimize(
            sum(costs) + sum(missing_flags) * shopping_weight + unique_cost + repetition_cost
        )

        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = SEARCH_WORKERS
        solver.parameters.random_seed = RANDOM_SEED
        solver.parameters.max_time_in_seconds = float(source.time_limit_seconds)
        solver.parameters.relative_gap_limit = float(source.relative_gap_limit)
        raw = solver.solve(model)
        status: Literal[
            "optimal",
            "feasible",
            "infeasible",
            "unknown",
            "invalid_model",
            "time_limit_without_solution",
        ] = self._status(raw, solver.wall_time)
        selected = (
            tuple(
                item.option_id
                for item in source.options
                if status in {"optimal", "feasible"} and solver.value(variables[item.option_id])
            )
            if status in {"optimal", "feasible"}
            else ()
        )
        objective = Decimal(str(solver.objective_value)) if selected else None
        bound = Decimal(str(solver.best_objective_bound)) if selected else None
        # CP-SAT may report OPTIMAL after satisfying a configured relative-gap limit. The product
        # reserves that word for a numerically closed model bound.
        if (
            status == "optimal"
            and objective is not None
            and bound is not None
            and objective != bound
        ):
            status = "feasible"
        relative_gap: Decimal | None = (
            abs(objective - bound) / max(abs(objective), Decimal(1))
            if objective is not None and bound is not None and status != "optimal"
            else Decimal(0)
            if status == "optimal"
            else None
        )
        binding = []
        if len(selected) == source.maximum_repetitions_week:
            binding.append("Maximale Rezeptwiederholungen können erreicht sein.")
        return SolverResult(
            status=status,
            selected_option_ids=selected,
            solve_time_seconds=Decimal(str(time.monotonic() - started)),
            objective_value=objective,
            best_objective_bound=bound,
            relative_gap=relative_gap,
            candidate_variable_count=len(variables),
            constraint_count=constraints,
            binding_constraints=tuple(binding),
        )

    @staticmethod
    def _nutrition_constraints(
        model: cp_model.CpModel,
        variables: dict[str, cp_model.IntVar],
        options: list[OptimizerOption],
        bounds: NutritionBounds,
        fixed: dict[str, Decimal],
        source: OptimizerInput,
    ) -> int:
        count = 0

        def total(code: str, kind: str) -> cp_model.LinearExpr:
            return cp_model.LinearExpr.sum(
                [scale(fixed.get(code, Decimal(0)), kind)]
                + [
                    variables[item.option_id] * scale(item.nutrients.get(code, Decimal(0)), kind)
                    for item in options
                ]
            )

        if source.strict_energy and bounds.energy_min is not None:
            model.add(
                total("energy_kcal", "energy_kcal")
                >= scale(bounds.energy_min, "energy_kcal", bound="lower")
            )
            count += 1
        if source.strict_energy and bounds.energy_max is not None:
            model.add(
                total("energy_kcal", "energy_kcal")
                <= scale(bounds.energy_max, "energy_kcal", bound="upper")
            )
            count += 1
        if source.strict_protein and bounds.protein_min is not None:
            model.add(
                total("protein", "macro_g") >= scale(bounds.protein_min, "macro_g", bound="lower")
            )
            count += 1
        if source.strict_fiber and bounds.fiber_min is not None:
            model.add(
                total("fiber", "macro_g") >= scale(bounds.fiber_min, "macro_g", bound="lower")
            )
            count += 1
        if bounds.fat_min is not None:
            model.add(total("fat", "macro_g") >= scale(bounds.fat_min, "macro_g", bound="lower"))
            count += 1
        if bounds.fat_max is not None:
            model.add(total("fat", "macro_g") <= scale(bounds.fat_max, "macro_g", bound="upper"))
            count += 1
        if bounds.saturated_fat_max is not None:
            model.add(
                total("saturated_fat", "macro_g")
                <= scale(bounds.saturated_fat_max, "macro_g", bound="upper")
            )
            count += 1
        return count

    @staticmethod
    def _status(
        raw: Any, wall_time: float
    ) -> Literal[
        "optimal",
        "feasible",
        "infeasible",
        "unknown",
        "invalid_model",
        "time_limit_without_solution",
    ]:
        if raw == cp_model.OPTIMAL:
            return "optimal"
        if raw == cp_model.FEASIBLE:
            return "feasible"
        if raw == cp_model.INFEASIBLE:
            return "infeasible"
        if raw == cp_model.MODEL_INVALID:
            return "invalid_model"
        return "time_limit_without_solution" if wall_time > 0 else "unknown"
