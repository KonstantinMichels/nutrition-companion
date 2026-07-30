from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.daily_meal_planning import repository
from app.modules.daily_meal_planning.engine import (
    ComponentValue,
    EntryInput,
    MealInput,
    calculate,
    compare_targets,
)
from app.modules.daily_meal_planning.enums import MEAL_LABELS_DE, EntryType, MealType
from app.modules.daily_meal_planning.models import DailyMealPlan, Meal, MealEntry
from app.modules.daily_meal_planning.schemas import (
    DailyPlanListResponse,
    DailyPlanResponse,
    DailyPlanWrite,
    DuplicatePlanRequest,
    MealEntryWrite,
    MealWrite,
)
from app.modules.foods import repository as food_repository
from app.modules.foods import service as food_service
from app.modules.foods.models import Food
from app.modules.nutrition_assessment import repository as assessment_repository
from app.modules.nutrition_assessment.models import Assessment
from app.modules.recipe_target_comparison.engine import TargetDescriptor
from app.modules.recipe_target_comparison.target_extraction import extract_targets, is_usable
from app.modules.recipes import repository as recipe_repository
from app.modules.recipes.engine.calculation import calculate_recipe
from app.modules.recipes.models import Recipe


def _error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def require(session: Session, profile_id: UUID, plan_id: UUID) -> DailyMealPlan:
    plan = repository.get(session, profile_id, plan_id)
    if plan is None:
        raise _error("DAILY_PLAN_NOT_FOUND", "Der Tagesplan wurde nicht gefunden.", 404)
    return plan


def _assessment(
    session: Session, profile_id: UUID, assessment_id: UUID | None, use_latest: bool
) -> Assessment | None:
    if assessment_id is not None:
        item = assessment_repository.get_assessment(session, profile_id, assessment_id)
        if item is None:
            raise _error(
                "ASSESSMENT_NOT_FOUND", "Das ausgewählte Assessment wurde nicht gefunden.", 404
            )
        if not is_usable(item):
            raise _error(
                "ASSESSMENT_NOT_COMPARABLE",
                "Dieses Assessment kann nicht für die Tagesplanung verwendet werden.",
                409,
            )
        return item
    if not use_latest:
        return None
    return next(
        (
            item
            for item in assessment_repository.list_assessments_with_metrics(session, profile_id)
            if is_usable(item)
        ),
        None,
    )


def _apply_structure(
    session: Session,
    profile_id: UUID,
    plan: DailyMealPlan,
    payload: DailyPlanWrite,
    *,
    allowed_archived_recipes: set[UUID] | None = None,
    allowed_archived_foods: set[UUID] | None = None,
) -> None:
    plan.plan_date = payload.plan_date
    plan.name = payload.name
    plan.notes = payload.notes
    selected = _assessment(
        session, profile_id, payload.assessment_id, payload.use_latest_assessment
    )
    plan.assessment_id = None if selected is None else selected.id
    if plan.training_day_adjustment is not None and (
        plan.training_day_adjustment.adjustment_date != payload.plan_date
        or plan.training_day_adjustment.source_assessment_id != plan.assessment_id
    ):
        plan.training_day_adjustment_id = None
    plan.meals.clear()
    for meal_position, source_meal in enumerate(payload.meals):
        meal = Meal(
            meal_type=source_meal.meal_type.value,
            custom_name=source_meal.custom_name,
            planned_time=source_meal.planned_time,
            position=meal_position,
            notes=source_meal.notes,
        )
        for entry_position, source_entry in enumerate(source_meal.entries):
            _validate_source(
                session,
                profile_id,
                source_entry,
                allowed_archived_recipes or set(),
                allowed_archived_foods or set(),
            )
            meal.entries.append(
                MealEntry(
                    entry_type=source_entry.entry_type.value,
                    recipe_id=source_entry.recipe_id,
                    food_id=source_entry.food_id,
                    recipe_portion_count=source_entry.recipe_portion_count,
                    food_quantity=source_entry.food_quantity,
                    food_unit_code=source_entry.food_unit_code,
                    food_measure_id=source_entry.food_measure_id,
                    position=entry_position,
                    note=source_entry.note,
                )
            )
        plan.meals.append(meal)


def _validate_source(
    session: Session,
    profile_id: UUID,
    entry: MealEntryWrite,
    allowed_archived_recipes: set[UUID],
    allowed_archived_foods: set[UUID],
) -> None:
    if entry.entry_type == EntryType.RECIPE:
        assert entry.recipe_id is not None
        recipe = recipe_repository.get(session, profile_id, entry.recipe_id)
        if recipe is None:
            raise _error(
                "ENTRY_SOURCE_NOT_FOUND", "Das ausgewählte Rezept wurde nicht gefunden.", 404
            )
        if recipe.is_archived and recipe.id not in allowed_archived_recipes:
            raise _error(
                "ENTRY_SOURCE_ARCHIVED",
                "Archivierte Rezepte können nicht neu hinzugefügt werden.",
                409,
            )
        return
    assert entry.food_id is not None and entry.food_quantity is not None
    food = food_repository.get_food(session, profile_id, entry.food_id)
    if food is None:
        raise _error(
            "ENTRY_SOURCE_NOT_FOUND", "Das ausgewählte Lebensmittel wurde nicht gefunden.", 404
        )
    if food.is_archived and food.id not in allowed_archived_foods:
        raise _error(
            "ENTRY_SOURCE_ARCHIVED",
            "Archivierte Lebensmittel können nicht neu hinzugefügt werden.",
            409,
        )
    try:
        _normalize_food(food, entry.food_quantity, entry.food_unit_code, entry.food_measure_id)
    except ApiError as exc:
        raise _error("ENTRY_NORMALIZATION_FAILED", exc.message) from exc


def create(session: Session, profile_id: UUID, payload: DailyPlanWrite) -> DailyPlanResponse:
    if repository.by_date(session, profile_id, payload.plan_date) is not None:
        raise _error(
            "DAILY_PLAN_ALREADY_EXISTS",
            "Für dieses Datum besteht bereits ein aktiver Tagesplan.",
            409,
        )
    plan = DailyMealPlan(owner_profile_id=profile_id, plan_date=payload.plan_date)
    session.add(plan)
    try:
        _apply_structure(session, profile_id, plan, payload)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _error(
            "DAILY_PLAN_ALREADY_EXISTS",
            "Für dieses Datum besteht bereits ein aktiver Tagesplan.",
            409,
        ) from exc
    return serialize(require(session, profile_id, plan.id))


def update(
    session: Session, profile_id: UUID, plan_id: UUID, payload: DailyPlanWrite
) -> DailyPlanResponse:
    plan = require(session, profile_id, plan_id)
    if plan.is_archived:
        raise _error("DAILY_PLAN_ARCHIVED", "Ein archivierter Tagesplan ist schreibgeschützt.", 409)
    conflict = repository.by_date(session, profile_id, payload.plan_date)
    if conflict is not None and conflict.id != plan.id:
        raise _error(
            "DAILY_PLAN_ALREADY_EXISTS",
            "Für dieses Datum besteht bereits ein aktiver Tagesplan.",
            409,
        )
    archived_recipes = {
        entry.recipe_id
        for meal in plan.meals
        for entry in meal.entries
        if entry.recipe_id is not None
    }
    archived_foods = {
        entry.food_id for meal in plan.meals for entry in meal.entries if entry.food_id is not None
    }
    _apply_structure(
        session,
        profile_id,
        plan,
        payload,
        allowed_archived_recipes=archived_recipes,
        allowed_archived_foods=archived_foods,
    )
    session.commit()
    return serialize(require(session, profile_id, plan.id))


def preview(session: Session, profile_id: UUID, payload: DailyPlanWrite) -> DailyPlanResponse:
    assessment = _assessment(
        session, profile_id, payload.assessment_id, payload.use_latest_assessment
    )
    meals = _preview_inputs(session, profile_id, payload.meals)
    return _response(
        plan=None,
        plan_date=payload.plan_date,
        name=payload.name,
        notes=payload.notes,
        assessment=assessment,
        meals=meals,
    )


def serialize(plan: DailyMealPlan) -> DailyPlanResponse:
    meals, assessment = _model_inputs(plan), plan.assessment
    if assessment is not None and not is_usable(assessment):
        assessment = None
    return _response(
        plan=plan,
        plan_date=plan.plan_date,
        name=plan.name,
        notes=plan.notes,
        assessment=assessment,
        meals=meals,
    )


def _response(
    *,
    plan: DailyMealPlan | None,
    plan_date: date,
    name: str | None,
    notes: str | None,
    assessment: Assessment | None,
    meals: tuple[MealInput, ...],
) -> DailyPlanResponse:
    result = calculate(meals)
    daily_totals = cast(list[dict[str, object]], result["daily_totals"])
    result_warnings = cast(list[dict[str, object]], result["warnings"])
    comparisons: list[dict[str, object]] = []
    comparison_warnings: list[dict[str, object]] = []
    adjustment = None if plan is None else plan.training_day_adjustment
    targets = extract_targets(assessment) if assessment is not None else []
    if adjustment is not None and assessment is not None:
        targets = _adjusted_targets(targets, adjustment)
    if assessment is not None:
        comparisons, comparison_warnings = compare_targets(daily_totals, targets)
    else:
        result_warnings.append(
            {
                "code": "NO_USABLE_ASSESSMENT",
                "severity": "info",
                "explanation_de": (
                    "Ohne geeignetes Assessment ist kein persönlicher Tagesvergleich verfügbar."
                ),
                "meal_id": None,
                "entry_id": None,
                "nutrient_code": None,
                "suggested_action_de": "Du kannst ein Assessment erstellen oder später auswählen.",
            }
        )
    return DailyPlanResponse.model_validate(
        {
            "plan": {
                "id": None if plan is None else plan.id,
                "plan_date": plan_date,
                "name": name,
                "notes": notes,
                "is_archived": False if plan is None else plan.is_archived,
                "archived_at": None if plan is None else plan.archived_at,
                "created_at": None if plan is None else plan.created_at,
                "updated_at": None if plan is None else plan.updated_at,
            },
            "assessment": None
            if assessment is None
            else {
                "id": assessment.id,
                "calculated_at": assessment.calculated_at,
                "goal_type": assessment.summary.get("goal_type", "unknown"),
                "reference_set_version": assessment.reference_set_version,
                "application_rule_set_version": assessment.application_rule_set_version,
            },
            "meals": result["meals"],
            "daily_totals": result["daily_totals"],
            "target_comparison": comparisons,
            "quality": result["quality"],
            "warnings": [*result_warnings, *comparison_warnings],
            "calculated_at": datetime.now(UTC),
            "notices": [
                "Der Tagesplan beschreibt geplante Mengen und bestätigt keinen "
                "tatsächlichen Verzehr.",
                "Der Tagesvergleich verwendet die unveränderten Zielwerte des gewählten "
                "Assessments sowie die aktuellen Nährwertdaten der enthaltenen Lebensmittel "
                "und Rezepte.",
            ],
            "target_basis": {
                "baseline_assessment_id": None if assessment is None else assessment.id,
                "baseline_energy_target_kcal": (
                    None if adjustment is None else adjustment.baseline_energy_target_kcal
                ),
                "training_day_adjustment_id": None if adjustment is None else adjustment.id,
                "training_adjustment_strategy": None if adjustment is None else adjustment.strategy,
                "training_adjustment_energy_delta_kcal": (
                    None if adjustment is None else adjustment.energy_delta_kcal
                ),
                "effective_energy_target_kcal": (
                    None if adjustment is None else adjustment.adjusted_energy_target_kcal
                ),
                "description_de": (
                    "Unverändertes Basisziel"
                    if adjustment is None
                    else "Für diesen Tag ausdrücklich verknüpfte temporäre Zielanpassung"
                ),
            },
        }
    )


def _adjusted_targets(targets: list[TargetDescriptor], adjustment: Any) -> list[TargetDescriptor]:
    output: list[TargetDescriptor] = []
    for target in targets:
        if target.nutrient_code == "energy_kcal":
            delta = adjustment.energy_delta_kcal
        elif target.nutrient_code == "carbohydrate":
            delta = adjustment.carbohydrate_delta_g
        else:
            output.append(target)
            continue
        output.append(
            TargetDescriptor(
                nutrient_code=target.nutrient_code,
                display_name_de=target.display_name_de,
                target_kind=target.target_kind,
                value=None if target.value is None else target.value + delta,
                minimum=None if target.minimum is None else target.minimum + delta,
                maximum=None if target.maximum is None else target.maximum + delta,
                unit=target.unit,
                category=target.category,
                display_order=target.display_order,
            )
        )
    return output


def _model_inputs(plan: DailyMealPlan) -> tuple[MealInput, ...]:
    recipe_cache: dict[UUID, dict[str, object]] = {}
    return tuple(
        MealInput(
            meal_id=meal.id,
            position=position,
            meal_type=meal.meal_type,
            meal_name=meal.custom_name or MEAL_LABELS_DE[MealType(meal.meal_type)],
            planned_time=meal.planned_time,
            notes=meal.notes,
            entries=tuple(
                _entry_input(entry, entry.position, recipe_cache)
                for entry in sorted(meal.entries, key=lambda item: item.position)
            ),
        )
        for position, meal in enumerate(sorted(plan.meals, key=lambda item: item.position))
    )


def _preview_inputs(
    session: Session, profile_id: UUID, meals: list[MealWrite]
) -> tuple[MealInput, ...]:
    recipe_cache: dict[UUID, dict[str, object]] = {}
    output: list[MealInput] = []
    for meal_position, meal in enumerate(meals):
        entries: list[EntryInput] = []
        for entry_position, entry in enumerate(meal.entries):
            _validate_source(session, profile_id, entry, set(), set())
            if entry.entry_type == EntryType.RECIPE:
                assert entry.recipe_id is not None
                recipe = recipe_repository.get(session, profile_id, entry.recipe_id)
                assert recipe is not None
                model = MealEntry(
                    entry_type="recipe",
                    recipe=recipe,
                    recipe_id=recipe.id,
                    recipe_portion_count=entry.recipe_portion_count,
                    position=entry_position,
                    note=entry.note,
                )
            else:
                assert entry.food_id is not None
                food = food_repository.get_food(session, profile_id, entry.food_id)
                assert food is not None
                measure = next(
                    (item for item in food.measures if item.id == entry.food_measure_id), None
                )
                model = MealEntry(
                    entry_type="food",
                    food=food,
                    food_id=food.id,
                    food_quantity=entry.food_quantity,
                    food_unit_code=entry.food_unit_code,
                    food_measure_id=entry.food_measure_id,
                    food_measure=measure,
                    position=entry_position,
                    note=entry.note,
                )
            entries.append(_entry_input(model, entry_position, recipe_cache))
        output.append(
            MealInput(
                None,
                meal_position,
                meal.meal_type.value,
                meal.custom_name or MEAL_LABELS_DE[meal.meal_type],
                meal.planned_time,
                meal.notes,
                tuple(entries),
            )
        )
    return tuple(output)


def _entry_input(
    entry: MealEntry, position: int, recipe_cache: dict[UUID, dict[str, object]]
) -> EntryInput:
    if entry.entry_type == "recipe":
        assert entry.recipe is not None and entry.recipe_portion_count is not None
        recipe: Recipe = entry.recipe
        calculation: Any = recipe_cache.setdefault(recipe.id, calculate_recipe(recipe))
        nutrients = tuple(
            ComponentValue(
                nutrient_code=str(item["nutrient_code"]),
                amount=Decimal(item["amount_per_serving"]) * entry.recipe_portion_count,
                unit=str(item["unit"]),
                known_count=int(item["known_ingredient_count"]),
                relevant_count=int(item["relevant_ingredient_count"]),
                missing_sources=tuple(
                    {
                        "meal_name": "",
                        "entry_name": recipe.name,
                        "source_name": str(missing["food_name"]),
                    }
                    for missing in item["missing_ingredients"]
                ),
            )
            for item in calculation["nutrients"]
        )
        warnings = []
        if recipe.is_archived:
            warnings.append(
                _warning(
                    "ARCHIVED_RECIPE_REFERENCE", "Das enthaltene Rezept ist archiviert.", entry.id
                )
            )
        if calculation["quality"]["archived_food_count"]:
            warnings.append(
                _warning(
                    "RECIPE_CONTAINS_ARCHIVED_FOOD",
                    "Das Rezept enthält mindestens ein archiviertes Lebensmittel.",
                    entry.id,
                )
            )
        return EntryInput(
            entry.id,
            position,
            "recipe",
            recipe.id,
            recipe.name,
            None,
            recipe.is_archived,
            entry.recipe_portion_count,
            None,
            None,
            None,
            None,
            None,
            False,
            entry.note,
            nutrients,
            tuple(warnings),
        )
    assert entry.food is not None and entry.food_quantity is not None
    food: Food = entry.food
    normalized, estimated, unit_code = _normalize_food(
        food, entry.food_quantity, entry.food_unit_code, entry.food_measure_id
    )
    serialized = food_service.serialize(food)
    nutrients = tuple(
        ComponentValue(
            item.nutrient_code, item.amount * normalized / food.reference_quantity, item.unit, 1, 1
        )
        for item in serialized.nutrients
    )
    warnings = []
    if food.is_archived:
        warnings.append(
            _warning(
                "ARCHIVED_FOOD_REFERENCE", "Das enthaltene Lebensmittel ist archiviert.", entry.id
            )
        )
    if estimated:
        warnings.append(
            _warning(
                "ESTIMATED_MEASURE_CONVERSION",
                "Die Umrechnung des Haushaltsmaßes ist geschätzt.",
                entry.id,
            )
        )
    return EntryInput(
        entry.id,
        position,
        "food",
        food.id,
        food.name,
        food.brand,
        food.is_archived,
        None,
        entry.food_quantity,
        unit_code,
        entry.food_measure_id,
        normalized,
        food.reference_unit,
        estimated,
        entry.note,
        nutrients,
        tuple(warnings),
    )


def _normalize_food(
    food: Food, quantity: Decimal, unit_code: str | None, measure_id: UUID | None
) -> tuple[Decimal, bool, str]:
    if measure_id is not None:
        measure = next((item for item in food.measures if item.id == measure_id), None)
        if measure is None:
            raise _error("ENTRY_MEASURE_INVALID", "Das Haushaltsmaß gehört nicht zum Lebensmittel.")
        base_quantity = measure.equivalent_quantity * quantity / measure.quantity
        return (
            food_service.normalize_base_quantity(food, base_quantity, measure.equivalent_unit),
            measure.is_estimated,
            measure.unit_code,
        )
    if unit_code not in {"g", "ml"}:
        raise _error(
            "ENTRY_UNIT_INCOMPATIBLE", "Bitte wähle eine kompatible Einheit oder ein Haushaltsmaß."
        )
    return food_service.normalize_base_quantity(food, quantity, unit_code), False, unit_code


def _warning(code: str, explanation: str, entry_id: UUID | None) -> dict[str, object]:
    return {
        "code": code,
        "severity": "warning",
        "explanation_de": explanation,
        "meal_id": None,
        "entry_id": entry_id,
        "nutrient_code": None,
        "suggested_action_de": "Der Eintrag kann ersetzt oder entfernt werden.",
    }


def list_plans(
    session: Session,
    profile_id: UUID,
    *,
    date_from: date | None,
    date_to: date | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> DailyPlanListResponse:
    items, total = repository.list_plans(
        session,
        profile_id,
        date_from=date_from,
        date_to=date_to,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return DailyPlanListResponse(
        items=[
            {
                "id": item.id,
                "plan_date": item.plan_date,
                "name": item.name,
                "is_archived": item.is_archived,
                "meal_count": len(item.meals),
                "entry_count": sum(len(meal.entries) for meal in item.meals),
                "assessment_id": item.assessment_id,
                "updated_at": item.updated_at,
            }
            for item in items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


def archive(session: Session, profile_id: UUID, plan_id: UUID) -> DailyMealPlan:
    plan = require(session, profile_id, plan_id)
    if not plan.is_archived:
        plan.is_archived = True
        plan.archived_at = datetime.now(UTC)
        session.commit()
    return plan


def restore(session: Session, profile_id: UUID, plan_id: UUID) -> DailyPlanResponse:
    plan = require(session, profile_id, plan_id)
    if not plan.is_archived:
        return serialize(plan)
    if repository.by_date(session, profile_id, plan.plan_date) is not None:
        raise _error(
            "TARGET_DATE_ALREADY_HAS_PLAN",
            "Für dieses Datum besteht bereits ein aktiver Tagesplan.",
            409,
        )
    plan.is_archived = False
    plan.archived_at = None
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _error(
            "TARGET_DATE_ALREADY_HAS_PLAN",
            "Für dieses Datum besteht bereits ein aktiver Tagesplan.",
            409,
        ) from exc
    return serialize(require(session, profile_id, plan.id))


def duplicate(
    session: Session, profile_id: UUID, plan_id: UUID, payload: DuplicatePlanRequest
) -> DailyPlanResponse:
    source = require(session, profile_id, plan_id)
    if repository.by_date(session, profile_id, payload.target_date) is not None:
        raise _error(
            "TARGET_DATE_ALREADY_HAS_PLAN",
            "Das Zieldatum enthält bereits einen aktiven Tagesplan.",
            409,
        )
    copy = DailyMealPlan(
        owner_profile_id=profile_id,
        plan_date=payload.target_date,
        assessment_id=source.assessment_id if payload.copy_assessment else None,
        name=source.name,
        notes=source.notes,
    )
    for meal in source.meals:
        meal_copy = Meal(
            meal_type=meal.meal_type,
            custom_name=meal.custom_name,
            planned_time=meal.planned_time,
            position=meal.position,
            notes=meal.notes,
        )
        for entry in meal.entries:
            meal_copy.entries.append(
                MealEntry(
                    entry_type=entry.entry_type,
                    recipe_id=entry.recipe_id,
                    food_id=entry.food_id,
                    recipe_portion_count=entry.recipe_portion_count,
                    food_quantity=entry.food_quantity,
                    food_unit_code=entry.food_unit_code,
                    food_measure_id=entry.food_measure_id,
                    position=entry.position,
                    note=entry.note,
                )
            )
        copy.meals.append(meal_copy)
    session.add(copy)
    session.commit()
    return serialize(require(session, profile_id, copy.id))
