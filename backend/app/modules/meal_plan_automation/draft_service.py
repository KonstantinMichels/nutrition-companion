from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.daily_meal_planning import repository as plan_repository
from app.modules.daily_meal_planning.models import DailyMealPlan, Meal, MealEntry
from app.modules.meal_plan_automation.engine import (
    Candidate,
    Component,
    portion_options,
    rank,
    target_fit,
)
from app.modules.meal_plan_automation.models import AutomationApplication
from app.modules.meal_plan_automation.schemas import ApplyRequest, GenerateRequest
from app.modules.meal_plan_automation.service import get
from app.modules.pantry import service as pantry_service
from app.modules.profiles import repository as profile_repository
from app.modules.recipe_target_comparison.service import _resolve_assessment
from app.modules.recipes import repository as recipe_repository
from app.modules.recipes.engine.calculation import calculate_recipe


def error(code: str, msg: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=msg, status_code=status)


def _dates(req: GenerateRequest) -> list[date]:
    if req.scope == "single_day":
        if req.plan_date is None:
            raise error("AUTOMATION_INVALID_DATE_RANGE", "Ein Datum ist erforderlich.")
        return [req.plan_date]
    if req.anchor_date is None:
        raise error("AUTOMATION_INVALID_DATE_RANGE", "Ein Wochendatum ist erforderlich.")
    start = req.anchor_date - timedelta(days=req.anchor_date.weekday())
    return [start + timedelta(days=i) for i in range(7)]


def _token(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _generate_greedy(session: Session, owner: UUID, req: GenerateRequest) -> dict[str, Any]:
    pref = get(session, owner, req.preferences_id)
    if pref.is_archived:
        raise error("AUTOMATION_PREFERENCES_ARCHIVED", "Die Einstellungen sind archiviert.", 409)
    assessment = _resolve_assessment(
        session,
        owner,
        pref.selected_assessment_id if pref.assessment_selection_mode == "explicit" else None,
    )
    if any(f.severity in {"blocking", "critical"} for f in assessment.safety_flags):
        raise error(
            "AUTOMATION_ASSESSMENT_NOT_SUPPORTED",
            "Diese Einschätzung unterstützt keine automatische Planung.",
            409,
        )
    recipes, _ = recipe_repository.list_recipes(
        session,
        owner,
        query=None,
        tag=None,
        include_archived=pref.allow_archived_recipe_candidates,
        page=1,
        page_size=100,
    )
    pantry = {r["food_id"]: r for r in pantry_service.availability(session, owner)}
    weights = {k: Decimal(v) for k, v in pref.scoring_weights.items()}
    profile = profile_repository.get_profile_record(session, owner)
    hard_food_exclusions = {
        restriction.value.strip().casefold()
        for restriction in (profile.restrictions if profile is not None else [])
        if restriction.restriction_type in {"allergy", "intolerance", "excluded_food"}
        and (restriction.hard_exclusion or restriction.restriction_type == "allergy")
    }
    energy_target = assessment.summary.get("energy_target", {})
    if not isinstance(energy_target, dict) or not energy_target.get("available"):
        raise error(
            "AUTOMATION_ASSESSMENT_NOT_SUPPORTED",
            "Die Einschätzung enthält kein verlässlich vergleichbares Energieziel.",
            409,
        )
    energy_low = Decimal(str(energy_target["lower"]))
    energy_high = Decimal(str(energy_target["upper"]))
    base = []
    excluded = []
    for recipe in recipes:
        reasons = []
        calc = calculate_recipe(recipe)
        if recipe.is_archived and not pref.allow_archived_recipe_candidates:
            reasons.append("AUTOMATION_RECIPE_ARCHIVED")
        if not recipe.ingredients:
            reasons.append("AUTOMATION_RECIPE_EMPTY")
        if str(recipe.id) in pref.excluded_recipe_ids:
            reasons.append("AUTOMATION_RECIPE_EXCLUDED")
        if set(recipe.tags) & set(pref.excluded_recipe_tag_codes):
            reasons.append("AUTOMATION_TAG_CONFLICT")
        if pref.enabled_recipe_tag_codes and not set(recipe.tags) & set(
            pref.enabled_recipe_tag_codes
        ):
            reasons.append("AUTOMATION_REQUIRED_TAG_MISSING")
        if any(
            ingredient.food.normalized_name.casefold() in hard_food_exclusions
            or ingredient.food.name.strip().casefold() in hard_food_exclusions
            for ingredient in recipe.ingredients
        ):
            reasons.append("AUTOMATION_NON_RELAXABLE_FOOD_EXCLUSION")
        total_time = (
            sum(
                v or 0
                for v in (
                    recipe.preparation_time_minutes,
                    recipe.cooking_time_minutes,
                    recipe.resting_time_minutes,
                )
            )
            or None
        )
        if pref.maximum_preparation_time_minutes is not None and (
            total_time is None or total_time > pref.maximum_preparation_time_minutes
        ):
            reasons.append("AUTOMATION_PREPARATION_TIME_EXCEEDED")
        if (
            not calc["quality"]["basic_nutrition_complete"]
            and not pref.allow_incomplete_basic_nutrition
        ):
            reasons.append("AUTOMATION_BASIC_NUTRITION_INCOMPLETE")
        available = sum(
            (
                pantry.get(i.food_id, {}).get("available_quantity", Decimal(0))
                >= i.normalized_quantity / recipe.servings
                for i in recipe.ingredients
            ),
            0,
        )
        pantry_score = (
            Decimal(available) / Decimal(len(recipe.ingredients))
            if recipe.ingredients
            else Decimal(0)
        )
        if pref.pantry_preference == "require_fully_available" and pantry_score < 1:
            reasons.append("AUTOMATION_PANTRY_NOT_FULLY_AVAILABLE")
        if reasons:
            excluded.append(
                {"recipe_id": recipe.id, "recipe_name": recipe.name, "exclusion_reasons": reasons}
            )
            continue
        base.append((recipe, calc, total_time, pantry_score))
    if not base:
        raise error(
            "AUTOMATION_NO_ELIGIBLE_CANDIDATES",
            "Für die gewählten Einstellungen wurden keine passenden Rezepte gefunden.",
            409,
        )
    days = []
    repetitions: dict[UUID, int] = {}
    last_used: dict[UUID, date] = {}
    pantry_budget = {fid: row["available_quantity"] for fid, row in pantry.items()}
    pantry_used: dict[UUID, Decimal] = {}
    shopping_missing: dict[UUID, Decimal] = {}
    weekly_totals: dict[str, Decimal] = {}
    for day in _dates(req):
        existing = plan_repository.by_date(session, owner, day)
        occupied = {m.meal_type for m in existing.meals} if existing else set()
        proposed = []
        totals: dict[str, Decimal] = {}
        for slot in [s for s in pref.slots if s.is_enabled]:
            key = f"{day}:{slot.slot_code}"
            if (
                key in req.removed_slot_keys
                or (req.existing_plan_mode == "empty_days_only" and existing)
                or (
                    req.existing_plan_mode == "empty_meal_slots_only" and slot.meal_type in occupied
                )
            ):
                continue
            candidates = []
            for recipe, calc, total_time, pantry_score in base:
                if repetitions.get(recipe.id, 0) >= pref.maximum_recipe_repetitions_per_week:
                    continue
                if (
                    recipe.id in last_used
                    and day > last_used[recipe.id]
                    and (day - last_used[recipe.id]).days <= pref.minimum_days_between_same_recipe
                ):
                    continue
                if slot.allowed_recipe_tag_codes and not set(recipe.tags) & set(
                    slot.allowed_recipe_tag_codes
                ):
                    continue
                if set(recipe.tags) & set(slot.excluded_recipe_tag_codes):
                    continue
                for portion in portion_options(
                    slot.portion_minimum, slot.portion_maximum, slot.portion_step
                ):
                    fit = Decimal(1) if slot.meal_type in recipe.tags else Decimal("0.5")
                    quality = (
                        Decimal(1)
                        if calc["quality"]["basic_nutrition_complete"]
                        else Decimal("0.5")
                    )
                    energy = next(
                        (
                            nutrient["amount_per_serving"] * portion
                            for nutrient in calc["nutrients"]
                            if nutrient["nutrient_code"] == "energy_kcal"
                        ),
                        None,
                    )
                    nutrition_fit = (
                        target_fit(
                            "range",
                            totals.get("energy_kcal", Decimal(0)) + energy,
                            energy_low,
                            None,
                            energy_high,
                        )
                        if energy is not None
                        else None
                    )
                    prep = (
                        None
                        if total_time is None
                        else max(
                            Decimal(0),
                            Decimal(1)
                            - Decimal(total_time)
                            / Decimal(
                                max(pref.maximum_preparation_time_minutes or total_time * 2, 1)
                            ),
                        )
                    )
                    components = (
                        Component("meal_slot_fit", fit, "Explizite Tags oder neutrale Zuordnung."),
                        Component(
                            "nutrition_target_fit",
                            nutrition_fit,
                            "Energiebeitrag im Verhältnis zum gespeicherten Tageszielbereich.",
                        ),
                        Component(
                            "pantry_availability",
                            pantry_score,
                            "Anteil der Zutaten im erfassten Vorrat.",
                        ),
                        Component("shopping_effort", pantry_score, "Weniger fehlende Zutaten."),
                        Component(
                            "preparation_time_fit", prep, "Abgleich mit der gewünschten Zeit."
                        ),
                        Component(
                            "recipe_variety",
                            Decimal(1) / (Decimal(1) + repetitions.get(recipe.id, 0)),
                            "Exakte Rezeptwiederholungen.",
                        ),
                        Component(
                            "recipe_preference",
                            Decimal("0.5"),
                            "Keine zusätzliche Präferenz hinterlegt.",
                        ),
                        Component("data_quality", quality, "Vollständigkeit der Nährwertdaten."),
                    )
                    candidates.append(
                        Candidate(
                            recipe.id,
                            recipe.name,
                            portion,
                            components,
                            preparation_minutes=total_time,
                        )
                    )
            ordered = rank(candidates, weights)
            if not ordered:
                proposed.append(
                    {
                        "slot_key": key,
                        "slot_code": slot.slot_code,
                        "meal_type": slot.meal_type,
                        "unresolved": True,
                        "explanation_de": (
                            "Für diesen Mahlzeiten-Slot wurden keine passenden Rezepte gefunden."
                        ),
                        "locked": False,
                    }
                )
                continue
            chosen = next(
                (r for r in ordered if str(r[0].recipe_id) == str(req.recipe_overrides.get(key))),
                ordered[0],
            )
            candidate, score = chosen
            portion = req.portion_overrides.get(key, candidate.portion)
            recipe, calc, _, _ = next(v for v in base if v[0].id == candidate.recipe_id)
            repetitions[recipe.id] = repetitions.get(recipe.id, 0) + 1
            last_used[recipe.id] = day
            for ingredient in recipe.ingredients:
                if ingredient.is_optional and not pref.include_optional_recipe_ingredients:
                    continue
                required = ingredient.normalized_quantity / recipe.servings * portion
                available_quantity = pantry_budget.get(ingredient.food_id, Decimal(0))
                used = min(available_quantity, required)
                pantry_budget[ingredient.food_id] = available_quantity - used
                pantry_used[ingredient.food_id] = (
                    pantry_used.get(ingredient.food_id, Decimal(0)) + used
                )
                missing = required - used
                if missing > 0:
                    shopping_missing[ingredient.food_id] = (
                        shopping_missing.get(ingredient.food_id, Decimal(0)) + missing
                    )
            for nutrient in calc["nutrients"]:
                totals[nutrient["nutrient_code"]] = (
                    totals.get(nutrient["nutrient_code"], Decimal(0))
                    + nutrient["amount_per_serving"] * portion
                )
                weekly_totals[nutrient["nutrient_code"]] = (
                    weekly_totals.get(nutrient["nutrient_code"], Decimal(0))
                    + nutrient["amount_per_serving"] * portion
                )
            proposed.append(
                {
                    "slot_key": key,
                    "slot_code": slot.slot_code,
                    "meal_type": slot.meal_type,
                    "custom_name": slot.custom_name,
                    "planned_time": slot.default_time,
                    "recipe_id": recipe.id,
                    "recipe_name": recipe.name,
                    "portion_count": portion,
                    "weighted_score": score,
                    "component_scores": [
                        {"code": c.code, "score": c.score, "explanation_de": c.explanation_de}
                        for c in candidate.components
                    ],
                    "selection_explanation": (
                        "Regelbasiert anhand deiner Einstellungen ausgewählt. "
                        "Vor dem Speichern prüfen."
                    ),
                    "alternatives": [
                        {
                            "recipe_id": c.recipe_id,
                            "recipe_name": c.recipe_name,
                            "portion_count": c.portion,
                            "weighted_score": s,
                        }
                        for c, s in ordered[1:6]
                    ],
                    "locked": key in req.locked_slot_keys,
                }
            )
        days.append(
            {
                "date": day,
                "existing_plan_id": existing.id if existing else None,
                "existing_plan_updated_at": existing.updated_at if existing else None,
                "proposed_meals": proposed,
                "projected_totals": [
                    {"nutrient_code": k, "amount": v} for k, v in sorted(totals.items())
                ],
            }
        )
    stable = {
        "preferences_updated_at": pref.updated_at,
        "assessment_id": assessment.id,
        "recipes": [(r.id, r.updated_at) for r, _, _, _ in base],
        "days": days,
        "pantry": sorted(
            ((str(food_id), quantity) for food_id, quantity in pantry_budget.items()),
            key=lambda item: item[0],
        ),
    }
    return {
        "engine": "greedy",
        "scope": req.scope,
        "date_from": _dates(req)[0],
        "date_to": _dates(req)[-1],
        "preferences_id": pref.id,
        "assessment": {"id": assessment.id, "calculated_at": assessment.calculated_at},
        "eligible_candidate_count": len(base),
        "excluded_candidates": excluded,
        "days": days,
        "weekly_projected_totals": [
            {"nutrient_code": code, "amount": amount}
            for code, amount in sorted(weekly_totals.items())
        ],
        "pantry_projection": {
            "notice": "Rechnerische Vorratsnutzung; nichts wird reserviert oder verändert.",
            "used": [
                {"food_id": food_id, "quantity": quantity}
                for food_id, quantity in sorted(pantry_used.items(), key=lambda item: str(item[0]))
            ],
        },
        "shopping_projection": {
            "notice": "Einkaufslisten werden nicht verändert.",
            "missing": [
                {"food_id": food_id, "quantity": quantity}
                for food_id, quantity in sorted(
                    shopping_missing.items(), key=lambda item: str(item[0])
                )
            ],
        },
        "warnings": [
            "Der Generator arbeitet deterministisch und gierig; der Entwurf ist nicht "
            "mathematisch optimal."
        ],
        "generated_at": datetime.now(UTC),
        "preview_token": _token(stable),
    }


def generate(session: Session, owner: UUID, req: GenerateRequest) -> dict[str, Any]:
    pref = get(session, owner, req.preferences_id)
    engine = req.generation_engine or pref.default_generation_engine
    if engine == "greedy":
        return _generate_greedy(session, owner, req)
    if not pref.optimizer_enabled:
        raise error(
            "AUTOMATION_OPTIMIZER_UNAVAILABLE",
            "Die gemeinsame Optimierung ist in diesem Einstellungsprofil deaktiviert.",
            409,
        )
    from app.modules.meal_plan_automation import optimizer_service

    return optimizer_service.generate(
        session, owner, req.model_copy(update={"generation_engine": engine}), pref
    )


def apply(session: Session, owner: UUID, payload: ApplyRequest) -> dict[str, Any]:
    existing = session.scalar(
        select(AutomationApplication).where(
            AutomationApplication.owner_profile_id == owner,
            AutomationApplication.client_operation_id == payload.client_operation_id,
        )
    )
    if existing:
        return {
            "application_id": existing.id,
            "applied_slot_count": existing.applied_slot_count,
            "references": existing.applied_references,
            "idempotent_replay": True,
        }
    draft = generate(session, owner, payload.generation)
    if draft["preview_token"] != payload.preview_token:
        raise error(
            "AUTOMATION_DRAFT_STALE",
            "Der Entwurf ist nicht mehr aktuell. Bitte neu berechnen.",
            409,
        )
    solver = draft.get("solver")
    if solver and solver.get("relaxation_used") and not payload.relaxation_confirmed:
        raise error(
            "AUTOMATION_OPTIMIZER_RELAXATION_CONFIRMATION_REQUIRED",
            "Bitte bestätige die angezeigten Regel-Lockerungen ausdrücklich.",
            409,
        )
    selected = set(payload.selected_slot_keys)
    conflicts: list[str] = []
    applied: list[dict[str, str]] = []
    try:
        for day in draft["days"]:
            proposals = [
                p
                for p in day["proposed_meals"]
                if "recipe_id" in p and (not selected or p["slot_key"] in selected)
            ]
            if not proposals:
                continue
            plan = plan_repository.by_date(session, owner, day["date"])
            if plan is None:
                if not payload.create_missing_plans:
                    conflicts.extend(p["slot_key"] for p in proposals)
                    continue
                plan = DailyMealPlan(
                    owner_profile_id=owner,
                    plan_date=day["date"],
                    assessment_id=UUID(draft["assessment"]["id"])
                    if isinstance(draft["assessment"]["id"], str)
                    else draft["assessment"]["id"],
                )
                session.add(plan)
                session.flush()
            occupied = {m.meal_type for m in plan.meals}
            for proposal in proposals:
                if proposal["meal_type"] in occupied:
                    conflicts.append(proposal["slot_key"])
                    continue
                meal = Meal(
                    daily_plan=plan,
                    meal_type=proposal["meal_type"],
                    custom_name=proposal["custom_name"],
                    planned_time=proposal["planned_time"],
                    position=max((m.position for m in plan.meals), default=-1) + 1,
                )
                session.add(meal)
                session.flush()
                entry = MealEntry(
                    meal=meal,
                    entry_type="recipe",
                    recipe_id=proposal["recipe_id"],
                    recipe_portion_count=proposal["portion_count"],
                    position=0,
                )
                session.add(entry)
                session.flush()
                occupied.add(proposal["meal_type"])
                applied.append(
                    {
                        "date": str(day["date"]),
                        "plan_id": str(plan.id),
                        "meal_id": str(meal.id),
                        "slot_key": proposal["slot_key"],
                    }
                )
        if conflicts and payload.application_mode == "all_or_nothing":
            raise error(
                "AUTOMATION_TARGET_SLOT_CONFLICT",
                "Mindestens ein Mahlzeiten-Slot wurde inzwischen belegt.",
                409,
            )
        audit = AutomationApplication(
            owner_profile_id=owner,
            scope=payload.generation.scope,
            date_from=draft["date_from"],
            date_to=draft["date_to"],
            automation_preferences_id=payload.generation.preferences_id,
            assessment_ids=[str(draft["assessment"]["id"])],
            applied_references=applied,
            applied_slot_count=len(applied),
            client_operation_id=payload.client_operation_id,
            generation_engine=draft.get("engine", "greedy"),
            solver_status=solver.get("status") if solver else None,
            solver_version=solver.get("version") if solver else None,
            objective_value=solver.get("objective_value") if solver else None,
            relative_gap=solver.get("relative_gap") if solver else None,
            relaxation_used=bool(solver and solver.get("relaxation_used")),
            relaxation_summary=draft.get("relaxations", []),
            objective_summary=draft.get("objective_breakdown", []),
            greedy_comparison_enabled=draft.get("greedy_comparison") is not None,
        )
        session.add(audit)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "application_id": audit.id,
        "applied_slot_count": len(applied),
        "references": applied,
        "conflicts": conflicts,
        "idempotent_replay": False,
    }
