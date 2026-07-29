from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.daily_meal_planning import repository as daily_repository
from app.modules.daily_meal_planning import service as daily_service
from app.modules.meal_plan_automation.models import AutomationPreferences
from app.modules.meal_plan_automation.optimizer.solver import (
    ORTOOLS_VERSION,
    CpSatMealPlanSolver,
    NutritionBounds,
    OptimizerInput,
    OptimizerOption,
    OptimizerSlot,
)
from app.modules.meal_plan_automation.schemas import GenerateRequest
from app.modules.pantry import service as pantry_service
from app.modules.recipe_target_comparison.target_extraction import extract_targets
from app.modules.recipes import repository as recipe_repository
from app.modules.recipes.engine.calculation import calculate_recipe
from app.modules.shopping_lists.models import ShoppingList


def _decimal(value: object | None, default: str = "0") -> Decimal:
    return Decimal(default if value is None else str(value))


def _nutrients(recipe: Any, portion: Decimal) -> dict[str, Decimal]:
    return {
        row["nutrient_code"]: row["amount_per_serving"] * portion
        for row in calculate_recipe(recipe)["nutrients"]
    }


def _requirements(recipe: Any, portion: Decimal, include_optional: bool) -> dict[UUID, Decimal]:
    return {
        ingredient.food_id: ingredient.normalized_quantity / recipe.servings * portion
        for ingredient in recipe.ingredients
        if include_optional or not ingredient.is_optional
    }


def generate(
    session: Session,
    owner: UUID,
    req: GenerateRequest,
    pref: AutomationPreferences,
) -> dict[str, Any]:
    from app.modules.meal_plan_automation.draft_service import _generate_greedy, _token

    baseline_request = req.model_copy(update={"generation_engine": "greedy"})
    baseline = _generate_greedy(session, owner, baseline_request)
    recipe_ids = {
        UUID(str(item["recipe_id"]))
        for day in baseline["days"]
        for proposal in day["proposed_meals"]
        if "recipe_id" in proposal
        for item in [proposal, *proposal.get("alternatives", [])]
    }
    recipes = {
        recipe_id: recipe_repository.get(session, owner, recipe_id) for recipe_id in recipe_ids
    }
    options: list[OptimizerOption] = []
    slots: list[OptimizerSlot] = []
    proposal_by_key: dict[str, dict[str, Any]] = {}
    considered = 0
    pruned = 0
    for day in baseline["days"]:
        for proposal in day["proposed_meals"]:
            if "recipe_id" not in proposal:
                continue
            key = proposal["slot_key"]
            proposal_by_key[key] = proposal
            slots.append(OptimizerSlot(key=key, day=day["date"], required=True))
            rows = [proposal, *proposal.get("alternatives", [])]
            considered += len(rows)
            rows = sorted(
                rows,
                key=lambda item: (
                    -_decimal(item.get("weighted_score"), "-1"),
                    str(item["recipe_name"]).casefold(),
                    str(item["recipe_id"]),
                    _decimal(item["portion_count"]),
                ),
            )
            manual_id = req.recipe_overrides.get(key)
            manual_portion = req.portion_overrides.get(key)
            limit = pref.solver_candidate_limit_per_slot
            kept = rows[:limit]
            for item in rows[limit:]:
                if str(item["recipe_id"]) == str(manual_id):
                    kept.append(item)
                else:
                    pruned += 1
            for item in kept:
                recipe_id = UUID(str(item["recipe_id"]))
                recipe = recipes[recipe_id]
                if recipe is None:
                    continue
                portion = _decimal(item["portion_count"])
                option_id = f"{key}|{recipe_id}|{portion}"
                components = {
                    value["code"]: _decimal(value.get("score"))
                    for value in proposal.get("component_scores", [])
                    if value.get("score") is not None
                }
                options.append(
                    OptimizerOption(
                        option_id=option_id,
                        slot_key=key,
                        day=day["date"],
                        recipe_id=recipe_id,
                        portion=portion,
                        nutrients=_nutrients(recipe, portion),
                        food_requirements=_requirements(
                            recipe, portion, pref.include_optional_recipe_ingredients
                        ),
                        preparation_minutes=sum(
                            value or 0
                            for value in (
                                recipe.preparation_time_minutes,
                                recipe.cooking_time_minutes,
                                recipe.resting_time_minutes,
                            )
                        ),
                        suitability=_decimal(item.get("weighted_score"), "0.5"),
                        pantry_coverage=components.get("pantry_availability", Decimal("0.5")),
                        data_quality=components.get("data_quality", Decimal("0.5")),
                        manually_selected=str(recipe_id) == str(manual_id),
                        locked=key in req.locked_slot_keys
                        and (manual_id is None or str(recipe_id) == str(manual_id))
                        and (manual_portion is None or portion == manual_portion),
                    )
                )
    if len(options) > 4000 or len(slots) > 35:
        from app.modules.meal_plan_automation.draft_service import error

        raise error(
            "AUTOMATION_OPTIMIZER_CANDIDATE_LIMIT_EXCEEDED",
            "Der Optimierungsentwurf ist trotz Begrenzung zu groß.",
            422,
        )
    energy = baseline["assessment"]
    assessment = next(
        item
        for item in [
            __import__(
                "app.modules.recipe_target_comparison.service", fromlist=["_resolve_assessment"]
            )._resolve_assessment(session, owner, UUID(str(energy["id"])))
        ]
    )
    energy_target = assessment.summary.get("energy_target", {})
    targets = {target.nutrient_code: target for target in extract_targets(assessment)}
    protein = targets.get("protein")
    fiber = targets.get("fiber")
    fat = targets.get("fat")
    saturated = targets.get("saturated_fat")
    bounds = NutritionBounds(
        energy_min=_decimal(energy_target.get("lower")) if energy_target else None,
        energy_max=_decimal(energy_target.get("upper")) if energy_target else None,
        protein_min=protein.minimum if protein else None,
        fiber_min=fiber.minimum if fiber else None,
        fat_min=(
            fat.minimum if pref.strict_fat_range and fat and fat.target_kind == "range" else None
        ),
        fat_max=(
            fat.maximum if pref.strict_fat_range and fat and fat.target_kind == "range" else None
        ),
        saturated_fat_max=(
            saturated.maximum if pref.strict_saturated_fat_maximum and saturated else None
        ),
    )
    pantry = {
        UUID(str(row["food_id"])): _decimal(row["available_quantity"])
        for row in pantry_service.availability(session, owner)
    }
    shopping_commitments: dict[UUID, Decimal] = {}
    for shopping_list in session.scalars(
        select(ShoppingList)
        .where(
            ShoppingList.owner_profile_id == owner,
            ShoppingList.status == "open",
            ShoppingList.is_archived.is_(False),
        )
        .options(selectinload(ShoppingList.items))
    ):
        for item in shopping_list.items:
            if item.food_id is None or item.source_status != "current":
                continue
            planned = item.purchase_quantity or item.suggested_purchase_quantity or Decimal(0)
            remaining = max(Decimal(0), planned - item.pantry_transferred_quantity)
            shopping_commitments[item.food_id] = (
                shopping_commitments.get(item.food_id, Decimal(0)) + remaining
            )
    existing_nutrients: dict[Any, dict[str, Decimal]] = {}
    existing_recipe_dates: dict[UUID, list[Any]] = {}
    for day in baseline["days"]:
        plan = daily_repository.by_date(session, owner, day["date"])
        if plan is None:
            continue
        response = daily_service.serialize(plan)
        existing_nutrients[day["date"]] = {
            row.nutrient_code: row.amount for row in response.daily_totals if row.amount is not None
        }
        for meal in plan.meals:
            for entry in meal.entries:
                if entry.recipe_id is not None:
                    existing_recipe_dates.setdefault(entry.recipe_id, []).append(day["date"])
    optimizer_input = OptimizerInput(
        slots=tuple(slots),
        options=tuple(options),
        nutrition_by_day={slot.day: bounds for slot in slots},
        existing_nutrients_by_day=existing_nutrients,
        existing_recipe_dates={
            recipe_id: tuple(dates) for recipe_id, dates in existing_recipe_dates.items()
        },
        pantry=pantry,
        shopping_commitments=shopping_commitments,
        maximum_repetitions_week=pref.maximum_recipe_repetitions_per_week,
        maximum_repetitions_day=pref.maximum_recipe_repetitions_per_day,
        minimum_day_gap=pref.minimum_days_between_same_recipe,
        maximum_daily_preparation_minutes=(
            pref.maximum_daily_preparation_time_minutes
            if pref.strict_daily_preparation_time
            else None
        ),
        maximum_unique_shopping_items=pref.maximum_weekly_unique_shopping_items,
        strict_energy=pref.strict_energy_target,
        strict_protein=pref.strict_protein_minimum,
        strict_fiber=pref.strict_fiber_minimum,
        strict_pantry=pref.pantry_preference == "require_fully_available",
        objective_weights={key: Decimal(value) for key, value in pref.objective_weights.items()},
        meal_prep_preference=cast(
            Literal["neutral", "prefer_reuse", "prefer_variety"], pref.meal_prep_preference
        ),
        time_limit_seconds=Decimal(
            pref.solver_time_limit_day_seconds
            if req.scope == "single_day"
            else pref.solver_time_limit_week_seconds
        ),
        relative_gap_limit=pref.solver_relative_gap_limit,
    )
    solver = CpSatMealPlanSolver()
    result = solver.solve(optimizer_input)
    relaxations: list[dict[str, str]] = []
    strict_status = result.status
    if (
        result.status == "infeasible"
        and req.generation_engine == "optimizer_explainable_relaxation"
        and pref.constraint_relaxation_enabled
    ):
        relaxed = replace(
            optimizer_input,
            maximum_repetitions_week=max(len(slots), optimizer_input.maximum_repetitions_week),
            minimum_day_gap=0,
            maximum_daily_preparation_minutes=None,
            maximum_unique_shopping_items=None,
            strict_energy=False,
            strict_protein=False,
            strict_fiber=False,
            strict_pantry=False,
        )
        result = solver.solve(relaxed)
        if result.status in {"optimal", "feasible"}:
            relaxations = [
                {
                    "code": "configured_flexible_constraints",
                    "explanation_de": (
                        "Konfigurierte Wiederholungs-, Zeit-, Vorrats- oder Zielregeln "
                        "wurden gelockert. Sicherheits- und Ausschlussregeln blieben aktiv."
                    ),
                }
            ]
    if result.status not in {"optimal", "feasible"}:
        return {
            "engine": "optimizer",
            "scope": req.scope,
            # Preserve the normal draft contract for the fallback UI as well.
            "assessment": baseline.get("assessment"),
            "solver": _solver_dict(result, optimizer_input, False),
            "candidate_summary": _candidate_summary(considered, options, pruned, slots),
            "infeasibility_reasons": [
                {
                    "code": "strict_combination_conflict",
                    "explanation_de": (
                        "Keine gemeinsame Kombination erfüllt alle aktiven strikten Regeln. "
                        "Prüfe Vorrat, Zeit, Wiederholungen, Sperren und strikte Zielbereiche."
                    ),
                }
            ],
            "relaxations": [],
            "warnings": ["Der schnelle regelbasierte Entwurf bleibt als Alternative verfügbar."],
            "days": baseline["days"],
            "preview_token": _token(
                {"baseline": baseline["preview_token"], "status": result.status}
            ),
        }
    selected = set(result.selected_option_ids)
    selected_options = {item.slot_key: item for item in options if item.option_id in selected}
    for day in baseline["days"]:
        replacements = []
        for proposal in day["proposed_meals"]:
            chosen = selected_options.get(proposal.get("slot_key"))
            if chosen is None:
                replacements.append(proposal)
                continue
            recipe = recipes[chosen.recipe_id]
            replacement = dict(proposal)
            replacement.update(
                recipe_id=chosen.recipe_id,
                recipe_name=recipe.name if recipe is not None else proposal["recipe_name"],
                portion_count=chosen.portion,
                optimizer_explanation=(
                    "Diese Auswahl unterstützt die beste gemeinsam gefundene Kombination unter "
                    "den gewählten Regeln, Gewichten und dem Zeitlimit."
                ),
                optimizer_effects={
                    "pantry_coverage": str(chosen.pantry_coverage),
                    "preparation_minutes": chosen.preparation_minutes,
                    "repetition_rule_satisfied": True,
                    "shopping_note_de": (
                        "Fehlmengen wurden gemeinsam mit Vorrat und offenen Einkaufszusagen "
                        "berechnet; keine Liste wurde verändert."
                    ),
                },
                alternatives=[
                    {
                        **alternative,
                        "non_selection_explanation_de": (
                            "Zulässige Alternative, aber durch die günstigere globale "
                            "Gesamtkombination verdrängt."
                        ),
                    }
                    for alternative in proposal.get("alternatives", [])
                ],
            )
            replacements.append(replacement)
        day["proposed_meals"] = replacements
    relaxation_used = bool(relaxations)
    solver_dict = _solver_dict(result, optimizer_input, relaxation_used)
    objective = _objective_breakdown(pref, selected_options)
    comparison = (
        {
            "changed_slot_count": sum(
                proposal_by_key[key]["recipe_id"] != option.recipe_id
                or _decimal(proposal_by_key[key]["portion_count"]) != option.portion
                for key, option in selected_options.items()
            ),
            "explanation_de": "Sachlicher Vergleich mit demselben schnellen Ausgangsentwurf.",
        }
        if pref.compare_with_greedy
        else None
    )
    baseline.update(
        engine="optimizer",
        solver=solver_dict,
        strict_solver_status=strict_status,
        candidate_summary=_candidate_summary(considered, options, pruned, slots),
        model_metrics={
            "slot_count": len(slots),
            "candidate_variable_count": result.candidate_variable_count,
            "constraint_count": result.constraint_count,
            "unique_recipe_count": len({item.recipe_id for item in options}),
            "unique_food_count": len({food for item in options for food in item.food_requirements}),
        },
        objective_breakdown=objective,
        binding_constraints=list(result.binding_constraints),
        relaxations=relaxations,
        greedy_comparison=comparison,
    )
    baseline["preview_token"] = _token(
        {
            "baseline": baseline["preview_token"],
            "engine": req.generation_engine,
            "selected": sorted(selected),
            "solver": {
                "status": solver_dict["status"],
                "version": solver_dict["version"],
                "objective_value": solver_dict["objective_value"],
                "relative_gap": solver_dict["relative_gap"],
                "relaxation_used": solver_dict["relaxation_used"],
            },
        }
    )
    return baseline


def _solver_dict(result: Any, source: OptimizerInput, relaxation_used: bool) -> dict[str, Any]:
    return {
        "status": result.status,
        "version": ORTOOLS_VERSION,
        "solve_time_seconds": result.solve_time_seconds,
        "time_limit_seconds": source.time_limit_seconds,
        "objective_value": result.objective_value,
        "best_objective_bound": result.best_objective_bound,
        "relative_gap": result.relative_gap,
        "relaxation_used": relaxation_used,
        "num_search_workers": 1,
        "random_seed": 0,
    }


def _candidate_summary(
    considered: int,
    options: list[OptimizerOption],
    pruned: int,
    slots: list[OptimizerSlot],
) -> dict[str, int]:
    return {
        "initial_candidate_count": considered,
        "eligible_candidate_count": considered,
        "pruned_candidate_count": pruned,
        "solver_candidate_count": len(options),
        "slot_count": len(slots),
    }


def _objective_breakdown(
    pref: AutomationPreferences, selected: dict[str, OptimizerOption]
) -> list[dict[str, Any]]:
    components = {
        "nutrition_fit": "Nährwertziele",
        "pantry_usage": "Vorrat",
        "shopping_effort": "Einkaufsbedarf",
        "preparation_time": "Zubereitungszeit",
        "variety": "Abwechslung",
        "meal_prep": "Meal-Prep-Potenzial",
        "recipe_preference": "Rezeptpräferenz",
        "data_quality": "Datenqualität",
    }
    rows = list(selected.values())
    count = Decimal(max(len(rows), 1))
    unique = Decimal(len({item.recipe_id for item in rows}))
    preparation = sum(Decimal(item.preparation_minutes or 120) for item in rows)
    normalized = {
        "nutrition_fit": sum((item.suitability for item in rows), Decimal(0)) / count,
        "pantry_usage": sum((item.pantry_coverage for item in rows), Decimal(0)) / count,
        "shopping_effort": sum((item.pantry_coverage for item in rows), Decimal(0)) / count,
        "preparation_time": max(Decimal(0), Decimal(1) - preparation / (count * 120)),
        "variety": unique / count,
        "meal_prep": Decimal(1) - (unique - Decimal(1)) / count if rows else Decimal(0),
        "recipe_preference": Decimal("0.5"),
        "data_quality": sum((item.data_quality for item in rows), Decimal(0)) / count,
    }
    result = []
    for code, label in components.items():
        value = min(Decimal(1), max(Decimal(0), normalized[code]))
        weight = Decimal(pref.objective_weights.get(code, "1"))
        result.append(
            {
                "component_code": code,
                "display_name_de": label,
                "raw_value": str(value),
                "normalization_reference": "0 bis 1",
                "normalized_value": str(value),
                "configured_weight": str(weight),
                "weighted_cost": str((Decimal(1) - value) * weight),
                "priority_stage": 3,
                "explanation_de": (
                    f"Normalisierter Beitrag für {len(selected)} gemeinsam ausgewählte Mahlzeiten."
                ),
            }
        )
    return result
