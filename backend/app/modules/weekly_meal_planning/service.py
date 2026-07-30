from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.daily_meal_planning import repository as daily_repository
from app.modules.daily_meal_planning import service as daily_service
from app.modules.daily_meal_planning.models import DailyMealPlan, Meal, MealEntry
from app.modules.recipe_target_comparison.unit_conversion import IncompatibleUnitError, convert
from app.modules.weekly_meal_planning.schemas import (
    MealTransferRequest,
    MealTransferResponse,
    WeeklyMealPlanResponse,
)

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def week_bounds(anchor: date) -> tuple[date, date, int, int]:
    start = anchor - timedelta(days=anchor.weekday())
    iso = start.isocalendar()
    return start, start + timedelta(days=6), iso.week, iso.year


def overview(
    session: Session, profile_id: UUID, anchor: date, *, include_archived_metadata: bool = True
) -> WeeklyMealPlanResponse:
    start, end, week_number, week_year = week_bounds(anchor)
    plans = daily_repository.in_date_range(session, profile_id, start, end)
    active = {item.plan_date: item for item in plans if not item.is_archived}
    archived_dates = {item.plan_date for item in plans if item.is_archived}
    days: list[dict[str, object]] = []
    results: list[tuple[date, Any]] = []
    counts = {
        "calendar_days": 7,
        "active_plan_days": 0,
        "planned_days": 0,
        "empty_plan_days": 0,
        "missing_plan_days": 0,
        "archived_only_days": 0,
        "comparable_target_days": 0,
        "complete_basic_nutrition_days": 0,
        "adjusted_day_count": 0,
        "unadjusted_day_count": 0,
        "redistribution_day_count": 0,
        "additive_day_count": 0,
    }
    for offset in range(7):
        day_date = start + timedelta(days=offset)
        plan = active.get(day_date)
        if plan is None:
            state = (
                "archived_only"
                if include_archived_metadata and day_date in archived_dates
                else "no_plan"
            )
            counts["missing_plan_days"] += 1
            if state == "archived_only":
                counts["archived_only_days"] += 1
            days.append(
                {
                    "date": day_date,
                    "weekday": WEEKDAYS[offset],
                    "state": state,
                    "plan": None,
                    "summary": {"meal_count": 0, "entry_count": 0},
                    "target_status": {"has_usable_assessment": False, "energy_relation": None},
                    "warnings": [],
                    "meals": [],
                }
            )
            continue
        result = daily_service.serialize(plan)
        basis = result.target_basis
        if basis.get("training_day_adjustment_id") is None:
            counts["unadjusted_day_count"] += 1
        else:
            counts["adjusted_day_count"] += 1
            if basis.get("training_adjustment_strategy") == "weekly_redistribution":
                counts["redistribution_day_count"] += 1
            elif basis.get("training_adjustment_strategy") == "bounded_additive":
                counts["additive_day_count"] += 1
        entry_count = result.quality.entry_count
        state = "planned" if entry_count else "empty_plan"
        counts["active_plan_days"] += 1
        counts["planned_days" if entry_count else "empty_plan_days"] += 1
        if entry_count:
            results.append((day_date, result))
            if result.assessment is not None:
                counts["comparable_target_days"] += 1
            if result.quality.basic_nutrition_complete:
                counts["complete_basic_nutrition_days"] += 1
        nutrients = {item.nutrient_code: item for item in result.daily_totals}
        energy_comparison = next(
            (item for item in result.target_comparison if item.nutrient_code == "energy_kcal"), None
        )
        day_warnings = [
            {
                "code": item.code,
                "severity": item.severity,
                "explanation_de": item.explanation_de,
                "date": day_date,
                "nutrient_code": item.nutrient_code,
                "suggested_action_de": item.suggested_action_de,
            }
            for item in result.warnings
            if item.code
            in {
                "ARCHIVED_RECIPE_REFERENCE",
                "ARCHIVED_FOOD_REFERENCE",
                "ESTIMATED_MEASURE_CONVERSION",
            }
        ]
        days.append(
            {
                "date": day_date,
                "weekday": WEEKDAYS[offset],
                "state": state,
                "plan": {
                    "id": plan.id,
                    "name": plan.name,
                    "assessment_id": plan.assessment_id,
                    "training_day_adjustment_id": plan.training_day_adjustment_id,
                    "is_archived": False,
                    "updated_at": plan.updated_at,
                },
                "summary": {
                    "meal_count": result.quality.meal_count,
                    "entry_count": entry_count,
                    "energy_kcal": _amount(nutrients, "energy_kcal"),
                    "protein_g": _amount(nutrients, "protein"),
                    "fat_g": _amount(nutrients, "fat"),
                    "carbohydrate_g": _amount(nutrients, "carbohydrate"),
                    "fiber_g": _amount(nutrients, "fiber"),
                    "basic_nutrition_complete": result.quality.basic_nutrition_complete,
                },
                "target_status": {
                    "has_usable_assessment": result.assessment is not None,
                    "energy_relation": None
                    if energy_comparison is None
                    else energy_comparison.relation,
                },
                "warnings": day_warnings,
                "meals": [
                    {
                        "id": meal.id,
                        "name": meal.meal_name,
                        "meal_type": meal.meal_type,
                        "entry_count": meal.entry_count,
                    }
                    for meal in result.meals
                ],
            }
        )
    totals = _weekly_totals(results)
    comparisons = _weekly_comparisons(results, totals)
    warnings = _weekly_warnings(counts, results, comparisons)
    redistribution_batches: dict[str, int] = {}
    for plan in active.values():
        adjustment = plan.training_day_adjustment
        if adjustment is not None and adjustment.strategy == "weekly_redistribution":
            redistribution_batches[str(adjustment.batch_id)] = (
                redistribution_batches.get(str(adjustment.batch_id), 0) + 1
            )
    if any(count < 7 for count in redistribution_batches.values()):
        warnings.append(
            {
                "code": "TRAINING_ADJUSTMENT_PARTIAL_WEEK_LINK",
                "severity": "info",
                "explanation_de": (
                    "Wöchentliche Umverteilung nur teilweise auf Tagespläne angewendet."
                ),
                "date": None,
                "nutrient_code": "energy_kcal",
                "suggested_action_de": "Die übrigen Tage werden nicht automatisch verknüpft.",
            }
        )
    planned = counts["planned_days"]
    complete = counts["complete_basic_nutrition_days"]
    quality_level = (
        "empty_week"
        if planned == 0
        else "partial_week"
        if planned < 7
        else "complete_week"
        if complete == 7
        else "planned_week"
    )
    assessments = {result.assessment.id for _, result in results if result.assessment is not None}
    return WeeklyMealPlanResponse.model_validate(
        {
            "week_start": start,
            "week_end": end,
            "iso_week_number": week_number,
            "iso_week_year": week_year,
            "days": days,
            "day_counts": counts,
            "weekly_totals": totals,
            "weekly_target_comparison": comparisons,
            "quality": {
                "quality_level": quality_level,
                "basic_nutrition_complete_day_count": complete,
                "basic_nutrition_incomplete_day_count": max(planned - complete, 0),
                "mixed_assessment_basis": len(assessments) > 1,
                "estimated_conversion_count": sum(
                    result.quality.estimated_conversion_count for _, result in results
                ),
                "archived_reference_count": sum(
                    result.quality.archived_recipe_count + result.quality.archived_food_count
                    for _, result in results
                ),
            },
            "warnings": warnings,
            "calculated_at": datetime.now(UTC),
            "notices": [
                "Fehlende Tagespläne werden nicht als Null-Verzehr interpretiert.",
                "Wochenmittelwerte beziehen sich ausschließlich auf geplante Tage.",
                "Die Wochenansicht ist eine aktuelle Ableitung und keine medizinische Bewertung.",
            ],
        }
    )


def _amount(items: dict[str, Any], code: str) -> Decimal | None:
    item = items.get(code)
    return None if item is None else item.amount


def _weekly_totals(results: list[tuple[date, Any]]) -> list[dict[str, object]]:
    codes: dict[str, list[tuple[date, Any]]] = {}
    for day_date, result in results:
        for item in result.daily_totals:
            codes.setdefault(item.nutrient_code, []).append((day_date, item))
    output = []
    planned_count = len(results)
    for code, values in codes.items():
        first = values[0][1]
        known = [(day_date, item) for day_date, item in values if item.amount is not None]
        amount = sum((item.amount for _, item in known), Decimal(0)) if known else None
        relevant = sum(item.relevant_component_count for _, item in values)
        known_components = sum(item.known_component_count for _, item in values)
        missing: list[dict[str, object]] = []
        for day_date, item in values:
            missing.extend(
                {"date": day_date, **source.model_dump()} for source in item.missing_sources
            )
        output.append(
            {
                "nutrient_code": code,
                "display_name_de": first.display_name_de,
                "category": first.category,
                "amount": amount,
                "average_per_planned_day": None
                if amount is None or planned_count == 0
                else amount / planned_count,
                "unit": first.unit,
                "planned_day_count": planned_count,
                "days_with_known_value": len(known),
                "days_with_complete_value": sum(item.is_complete for _, item in values),
                "coverage_ratio": None
                if relevant == 0
                else Decimal(known_components) / Decimal(relevant),
                "is_complete": len(values) == planned_count
                and all(item.is_complete for _, item in values),
                "missing_sources": missing[:50],
            }
        )
    return output


def _weekly_comparisons(
    results: list[tuple[date, Any]], totals: list[dict[str, object]]
) -> list[dict[str, object]]:
    total_by_code = {item["nutrient_code"]: item for item in totals}
    grouped: dict[str, list[tuple[date, Any, Any]]] = {}
    for day_date, result in results:
        if result.assessment is None:
            continue
        for item in result.target_comparison:
            if item.comparison_status != "unavailable":
                grouped.setdefault(item.nutrient_code, []).append(
                    (day_date, item, result.assessment)
                )
    output = []
    for code, values in grouped.items():
        first = values[0][1]
        kinds = {item.target_kind for _, item, _ in values}
        target_unit = first.target_unit
        compatible = len(kinds) == 1
        target_count = len(values)
        total = total_by_code.get(code, {})
        try:
            amount = _converted_sum(values, "amount", target_unit)
            minimum = _converted_sum(values, "target_minimum", target_unit)
            target = _converted_sum(values, "target_value", target_unit)
            maximum = _converted_sum(values, "target_maximum", target_unit)
        except IncompatibleUnitError:
            compatible = False
            amount = minimum = target = maximum = None
        complete = bool(total.get("is_complete"))
        relation, remaining, remaining_kind, remaining_status, percent, explanation = _relation(
            next(iter(kinds)) if compatible else None,
            amount,
            minimum,
            target,
            maximum,
            complete,
        )
        assessments = {assessment.id for _, _, assessment in values}
        references = {assessment.reference_set_version for _, _, assessment in values}
        rules = {assessment.application_rule_set_version for _, _, assessment in values}
        basis = (
            "incompatible_target_semantics"
            if not compatible
            else "incomplete_assessment_coverage"
            if target_count < len(results)
            else "single_assessment"
            if len(assessments) == 1
            else "multiple_compatible_assessments"
        )
        output.append(
            {
                "nutrient_code": code,
                "display_name_de": first.display_name_de,
                "category": first.category,
                "target_kind": next(iter(kinds)) if compatible else None,
                "amount": amount,
                "average_per_planned_day": None
                if amount is None or not results
                else amount / len(results),
                "unit": target_unit,
                "target_minimum": minimum,
                "target_value": target,
                "target_maximum": maximum,
                "target_day_count": target_count,
                "missing_target_day_count": len(results) - target_count,
                "relation": relation,
                "comparison_status": "available" if compatible else "unavailable",
                "remaining_amount": remaining,
                "remaining_kind": remaining_kind,
                "remaining_status": remaining_status,
                "contribution_percent": percent,
                "target_basis_status": basis,
                "assessment_ids": sorted(assessments, key=str),
                "reference_set_versions": sorted(references),
                "application_rule_set_versions": sorted(rules),
                "explanation_de": explanation,
                "coverage_ratio": total.get("coverage_ratio"),
            }
        )
    return output


def _converted_sum(values: list[tuple[date, Any, Any]], field: str, unit: str) -> Decimal | None:
    converted = [
        convert(value, item.target_unit, unit)
        for _, item, _ in values
        if (value := getattr(item, field)) is not None
    ]
    return sum(converted, Decimal(0)) if converted else None


def _relation(
    kind: str | None,
    amount: Any,
    minimum: Any,
    target: Any,
    maximum: Any,
    complete: bool,
) -> tuple[str, Decimal | None, str | None, str, Decimal | None, str]:
    if kind is None:
        return (
            "unavailable",
            None,
            None,
            "unavailable",
            None,
            "Die Tagesziele haben nicht kompatible Zielarten oder Einheiten.",
        )
    basis = target if kind == "reference" else minimum if kind == "minimum" else maximum
    percent = None if amount is None or basis in (None, 0) else amount / basis * 100
    if amount is None:
        return (
            "unknown",
            None,
            None,
            "unknown",
            percent,
            "Für diesen Wochenwert liegen keine bekannten Nährwertdaten vor.",
        )
    if kind == "minimum":
        remaining = max(minimum - amount, Decimal(0))
        relation = "at_or_above_minimum" if amount >= minimum else "below_minimum"
        status = "reliable" if complete else "upper_bound"
        text = (
            "Der geplante Wert erreicht den summierten Mindestwert."
            if amount >= minimum
            else (
                "Auf Basis der bekannten Daten fehlt höchstens ein Rest zum summierten Mindestwert."
                if not complete
                else "Der geplante Wert liegt unter dem summierten Mindestwert."
            )
        )
        return relation, remaining, "to_minimum", status, percent, text
    if kind == "maximum":
        exceeded = amount > maximum
        remaining = amount - maximum if exceeded else maximum - amount
        status = "reliable" if complete or exceeded else "indeterminate"
        text = (
            "Der bekannte geplante Wert überschreitet den summierten Tageshöchstwert."
            if exceeded
            else (
                "Die genaue verbleibende Menge ist wegen unvollständiger Daten unbekannt."
                if not complete
                else "Der geplante Wert liegt unter dem summierten Tageshöchstwert."
            )
        )
        return (
            "above_maximum" if exceeded else "within_maximum",
            remaining,
            "exceeded" if exceeded else "allowance",
            status,
            percent,
            text,
        )
    if kind == "range":
        if amount > maximum:
            return (
                "above_range",
                amount - maximum,
                "exceeded",
                "reliable",
                None,
                "Der bekannte geplante Wert liegt über dem summierten Zielbereich.",
            )
        if not complete:
            return (
                "indeterminate",
                None,
                None,
                "indeterminate",
                None,
                "Wegen unvollständiger Daten ist die Lage im summierten Zielbereich unbestimmt.",
            )
        if amount < minimum:
            return (
                "below_range",
                minimum - amount,
                "to_minimum",
                "reliable",
                None,
                "Der geplante Wert liegt unter dem summierten Zielbereich.",
            )
        return (
            "within_range",
            maximum - amount,
            "to_maximum",
            "reliable",
            None,
            "Der geplante Wert liegt innerhalb des summierten Zielbereichs.",
        )
    difference = None if target is None else target - amount
    return (
        "reference",
        difference,
        "difference",
        "reliable" if complete else "lower_bound",
        percent,
        "Der bekannte geplante Wert wird dem summierten Referenzwert gegenübergestellt.",
    )


def _weekly_warnings(
    counts: dict[str, int],
    results: list[tuple[date, Any]],
    comparisons: list[dict[str, object]],
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    if counts["planned_days"] == 0:
        warnings.append(
            {
                "code": "NO_PLANNED_DAYS",
                "severity": "info",
                "explanation_de": "Diese Woche enthält noch keine geplanten Einträge.",
            }
        )
    if counts["missing_plan_days"]:
        warnings.append(
            {
                "code": "MISSING_DAILY_PLANS",
                "severity": "info",
                "explanation_de": (
                    f"{counts['missing_plan_days']} Tage haben keinen aktiven Tagesplan."
                ),
            }
        )
    if counts["empty_plan_days"]:
        warnings.append(
            {
                "code": "EMPTY_DAILY_PLANS",
                "severity": "info",
                "explanation_de": (
                    f"{counts['empty_plan_days']} Tagespläne enthalten noch keine Einträge."
                ),
            }
        )
    if counts["comparable_target_days"] < counts["planned_days"]:
        warnings.append(
            {
                "code": "MISSING_DAILY_ASSESSMENTS",
                "severity": "info",
                "explanation_de": "Nicht alle geplanten Tage besitzen vergleichbare Zielwerte.",
            }
        )
    assessment_ids = {result.assessment.id for _, result in results if result.assessment}
    if len(assessment_ids) > 1:
        warnings.append(
            {
                "code": "MIXED_ASSESSMENT_BASIS",
                "severity": "info",
                "explanation_de": (
                    "Diese Woche verwendet unterschiedliche Assessments. Die Wochenziele "
                    "wurden aus den jeweiligen Tageszielen zusammengesetzt."
                ),
            }
        )
    if any(item["target_basis_status"] == "incompatible_target_semantics" for item in comparisons):
        warnings.append(
            {
                "code": "INCOMPATIBLE_TARGET_SEMANTICS",
                "severity": "warning",
                "explanation_de": (
                    "Einige Tagesziele besitzen nicht kompatible Zielarten oder Einheiten "
                    "und wurden nicht summiert."
                ),
            }
        )
    return warnings


def transfer_meal(
    session: Session,
    profile_id: UUID,
    payload: MealTransferRequest,
    *,
    move: bool,
) -> MealTransferResponse:
    source = daily_service.require(session, profile_id, payload.source_plan_id)
    if source.is_archived:
        raise daily_service._error(
            "MEAL_SOURCE_ARCHIVED", "Archivierte Mahlzeiten können nicht übertragen werden.", 409
        )
    source_meal = next((meal for meal in source.meals if meal.id == payload.source_meal_id), None)
    if source_meal is None:
        raise daily_service._error(
            "SOURCE_MEAL_NOT_FOUND", "Die Quellmahlzeit wurde nicht gefunden.", 404
        )
    target = daily_repository.by_date(session, profile_id, payload.target_date)
    if target is None:
        assessment = None
        if payload.assessment_copy_mode == "source":
            assessment = source.assessment_id
        elif payload.assessment_copy_mode == "latest":
            latest = daily_service._assessment(session, profile_id, None, True)
            assessment = None if latest is None else latest.id
        target = DailyMealPlan(
            owner_profile_id=profile_id, plan_date=payload.target_date, assessment_id=assessment
        )
        session.add(target)
        session.flush()
    if payload.copy_mode == "append_to_existing_meal":
        target_meal = next(
            (meal for meal in target.meals if meal.id == payload.target_meal_id), None
        )
        if target_meal is None:
            raise daily_service._error(
                "TARGET_MEAL_NOT_FOUND", "Die Zielmahlzeit wurde nicht gefunden.", 404
            )
        if move and target_meal.id == source_meal.id:
            raise daily_service._error(
                "TARGET_DATE_INVALID",
                "Eine Mahlzeit kann nicht an sich selbst angehängt werden.",
                409,
            )
        for entry in sorted(source_meal.entries, key=lambda item: item.position):
            target_meal.entries.append(_copy_entry(entry, len(target_meal.entries)))
    else:
        target_meal = Meal(
            meal_type=source_meal.meal_type,
            custom_name=source_meal.custom_name,
            planned_time=source_meal.planned_time,
            position=len(target.meals),
            notes=source_meal.notes,
        )
        for entry in sorted(source_meal.entries, key=lambda item: item.position):
            target_meal.entries.append(_copy_entry(entry, len(target_meal.entries)))
        target.meals.append(target_meal)
    if move:
        source.meals.remove(source_meal)
        for position, meal in enumerate(sorted(source.meals, key=lambda item: item.position)):
            meal.position = position
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise daily_service._error(
            "MEAL_MOVE_FAILED" if move else "MEAL_COPY_FAILED",
            "Die Mahlzeit konnte nicht übertragen werden.",
            409,
        ) from exc
    return MealTransferResponse(
        operation="move" if move else "copy",
        source_plan_id=source.id,
        target_plan_id=target.id,
        target_meal_id=target_meal.id,
        target_date=payload.target_date,
        message_de="Die Mahlzeit wurde verschoben." if move else "Die Mahlzeit wurde kopiert.",
    )


def _copy_entry(entry: MealEntry, position: int) -> MealEntry:
    return MealEntry(
        entry_type=entry.entry_type,
        recipe_id=entry.recipe_id,
        food_id=entry.food_id,
        recipe_portion_count=entry.recipe_portion_count,
        food_quantity=entry.food_quantity,
        food_unit_code=entry.food_unit_code,
        food_measure_id=entry.food_measure_id,
        position=position,
        note=entry.note,
    )
