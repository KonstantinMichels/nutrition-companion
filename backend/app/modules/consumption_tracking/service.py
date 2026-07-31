from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.daily_meal_planning import repository as plan_repository
from app.modules.daily_meal_planning import service as plan_service
from app.modules.daily_meal_planning.engine import compare_targets
from app.modules.daily_meal_planning.enums import MEAL_LABELS_DE, MealType
from app.modules.daily_meal_planning.models import MealEntry
from app.modules.daily_meal_planning.service import _adjusted_targets, _entry_input
from app.modules.foods import repository as food_repository
from app.modules.foods.nutrient_catalog import CORE_CODES, NUTRIENT_BY_CODE
from app.modules.nutrition_assessment import repository as assessment_repository
from app.modules.recipe_target_comparison.engine import TargetDescriptor
from app.modules.recipe_target_comparison.target_extraction import extract_targets, is_usable
from app.modules.recipes import repository as recipe_repository

from . import repository
from .enums import (
    Completeness,
    DayStatus,
    EntryType,
    OriginType,
    OutcomeType,
    SnapshotState,
    TargetBasisSource,
)
from .models import (
    ConsumptionDay,
    ConsumptionEntry,
    ConsumptionEntryNutrientSnapshot,
    ConsumptionMeal,
    PlannedEntryConsumptionOutcome,
)
from .schemas import (
    ConfirmWholeMeal,
    DayCreate,
    DayPatch,
    EntryWrite,
    FinalizeWrite,
    FromPlan,
    LinkDailyPlan,
    MealWrite,
    OutcomeWrite,
    ReorderMeals,
)


def error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def require_day(
    session: Session, profile_id: UUID, day_id: UUID, *, lock: bool = False
) -> ConsumptionDay:
    item = repository.get(session, profile_id, day_id, lock=lock)
    if item is None:
        raise error("CONSUMPTION_DAY_NOT_FOUND", "Der Verzehrtag wurde nicht gefunden.", 404)
    return item


def _open(day: ConsumptionDay, expected: int | None = None) -> None:
    if day.status == DayStatus.FINALIZED:
        raise error(
            "CONSUMPTION_DAY_FINALIZED",
            "Der abgeschlossene Tag muss zuerst wieder geöffnet werden.",
            409,
        )
    if expected is not None and day.version != expected:
        raise error(
            "CONSUMPTION_CONCURRENT_MODIFICATION",
            "Der Tag wurde zwischenzeitlich geändert. Bitte lade ihn neu.",
            409,
        )


def _latest_usable(session: Session, profile_id: UUID) -> Any:
    return next(
        (
            a
            for a in assessment_repository.list_assessments_with_metrics(session, profile_id)
            if is_usable(a)
        ),
        None,
    )


def create_day(session: Session, profile_id: UUID, payload: DayCreate) -> dict[str, Any]:
    if payload.consumption_date > date.today():
        raise error(
            "CONSUMPTION_DAY_FUTURE_DATE_NOT_ALLOWED",
            "Tatsächlicher Verzehr kann nicht für einen zukünftigen Tag erfasst werden.",
        )
    if repository.by_date(session, profile_id, payload.consumption_date):
        raise error(
            "CONSUMPTION_DAY_ALREADY_EXISTS",
            "Für dieses Datum besteht bereits ein Verzehrtag.",
            409,
        )
    assessment = None
    if payload.target_basis_source == TargetBasisSource.EXPLICIT:
        if payload.assessment_id is None:
            raise error("CONSUMPTION_TARGET_BASIS_INVALID", "Bitte wähle eine Einschätzung aus.")
        assessment = assessment_repository.get_assessment(
            session, profile_id, payload.assessment_id
        )
        if assessment is None or not is_usable(assessment):
            raise error(
                "CONSUMPTION_TARGET_BASIS_INVALID", "Die Einschätzung ist nicht verwendbar.", 409
            )
    elif payload.target_basis_source == TargetBasisSource.LATEST:
        assessment = _latest_usable(session, profile_id)
    day = ConsumptionDay(
        owner_profile_id=profile_id,
        consumption_date=payload.consumption_date,
        assessment_id=None if assessment is None else assessment.id,
        target_basis_source=payload.target_basis_source.value,
        target_basis_snapshot=_basis_snapshot(assessment, None),
        note=payload.note,
    )
    session.add(day)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise error(
            "CONSUMPTION_DAY_ALREADY_EXISTS",
            "Für dieses Datum besteht bereits ein Verzehrtag.",
            409,
        ) from exc
    return detail(require_day(session, profile_id, day.id))


def from_plan(session: Session, profile_id: UUID, payload: FromPlan) -> dict[str, Any]:
    plan = plan_repository.get(session, profile_id, payload.daily_plan_id)
    if plan is None:
        raise error("CONSUMPTION_PLAN_NOT_FOUND", "Der Tagesplan wurde nicht gefunden.", 404)
    if repository.by_date(session, profile_id, plan.plan_date):
        raise error(
            "CONSUMPTION_DAY_ALREADY_EXISTS",
            "Für dieses Datum besteht bereits ein Verzehrtag.",
            409,
        )
    if plan.plan_date > date.today():
        raise error(
            "CONSUMPTION_DAY_FUTURE_DATE_NOT_ALLOWED",
            "Ein zukünftiger Tagesplan kann noch nicht als tatsächlicher "
            "Verzehr übernommen werden.",
        )
    day = ConsumptionDay(
        owner_profile_id=profile_id,
        consumption_date=plan.plan_date,
        source_daily_plan_id=plan.id,
        assessment_id=plan.assessment_id,
        training_day_adjustment_id=plan.training_day_adjustment_id,
        target_basis_source=TargetBasisSource.DAILY_PLAN.value,
        target_basis_snapshot=_basis_snapshot(plan.assessment, plan.training_day_adjustment),
        note=payload.note,
    )
    for position, meal in enumerate(plan.meals):
        day.meals.append(
            ConsumptionMeal(
                meal_type=meal.meal_type,
                custom_name=meal.custom_name,
                consumed_time=meal.planned_time,
                position=position,
                source_plan_meal_id=meal.id,
                source_plan_meal_name_snapshot=meal.custom_name
                or MEAL_LABELS_DE[MealType(meal.meal_type)],
            )
        )
    session.add(day)
    session.commit()
    return detail(require_day(session, profile_id, day.id))


def _basis_snapshot(assessment: Any, adjustment: Any) -> dict[str, Any]:
    baseline_targets = [] if assessment is None else extract_targets(assessment)
    effective_targets = (
        baseline_targets if adjustment is None else _adjusted_targets(baseline_targets, adjustment)
    )
    energy_target = (
        None
        if assessment is None
        else next(
            (item for item in extract_targets(assessment) if item.nutrient_code == "energy_kcal"),
            None,
        )
    )
    baseline = (
        adjustment.baseline_energy_target_kcal
        if adjustment is not None
        else None
        if energy_target is None
        else energy_target.value
    )
    return {
        "assessment_id": None if assessment is None else str(assessment.id),
        "assessment_calculated_at": None
        if assessment is None
        else assessment.calculated_at.isoformat(),
        "training_day_adjustment_id": None if adjustment is None else str(adjustment.id),
        "baseline_energy_target_kcal": None if baseline is None else str(baseline),
        "baseline_energy_minimum_kcal": None
        if energy_target is None or energy_target.minimum is None
        else str(energy_target.minimum),
        "baseline_energy_maximum_kcal": None
        if energy_target is None or energy_target.maximum is None
        else str(energy_target.maximum),
        "energy_delta_kcal": None if adjustment is None else str(adjustment.energy_delta_kcal),
        "effective_energy_target_kcal": str(adjustment.adjusted_energy_target_kcal)
        if adjustment is not None
        else None
        if baseline is None
        else str(baseline),
        "baseline_targets": [_target_snapshot(item) for item in baseline_targets],
        "effective_targets": [_target_snapshot(item) for item in effective_targets],
    }


def _target_snapshot(target: TargetDescriptor) -> dict[str, Any]:
    return {
        "nutrient_code": target.nutrient_code,
        "display_name_de": target.display_name_de,
        "target_kind": target.target_kind,
        "value": None if target.value is None else str(target.value),
        "minimum": None if target.minimum is None else str(target.minimum),
        "maximum": None if target.maximum is None else str(target.maximum),
        "unit": target.unit,
        "category": target.category,
        "display_order": target.display_order,
    }


def _targets_from_snapshot(day: ConsumptionDay) -> list[TargetDescriptor]:
    return [
        TargetDescriptor(
            nutrient_code=item["nutrient_code"],
            display_name_de=item["display_name_de"],
            target_kind=item["target_kind"],
            value=None if item.get("value") is None else Decimal(item["value"]),
            minimum=None if item.get("minimum") is None else Decimal(item["minimum"]),
            maximum=None if item.get("maximum") is None else Decimal(item["maximum"]),
            unit=item["unit"],
            category=item["category"],
            display_order=int(item["display_order"]),
        )
        for item in day.target_basis_snapshot.get("effective_targets", [])
    ]


def patch_day(
    session: Session, profile_id: UUID, day_id: UUID, payload: DayPatch
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day, payload.expected_version)
    day.note = payload.note
    if payload.target_basis_source is not None:
        if not payload.confirm_target_basis_change:
            raise error(
                "CONSUMPTION_TARGET_BASIS_INVALID",
                "Bitte bestätige die Änderung der historischen Zielbasis ausdrücklich.",
                409,
            )
        assessment = None
        adjustment = None
        if payload.target_basis_source == TargetBasisSource.EXPLICIT:
            if payload.assessment_id is None:
                raise error("CONSUMPTION_TARGET_BASIS_INVALID", "Bitte wähle eine Einschätzung.")
            assessment = assessment_repository.get_assessment(
                session, profile_id, payload.assessment_id
            )
            if assessment is None or not is_usable(assessment):
                raise error(
                    "CONSUMPTION_TARGET_BASIS_INVALID",
                    "Die ausgewählte Einschätzung ist nicht verwendbar.",
                    409,
                )
        elif payload.target_basis_source == TargetBasisSource.LATEST:
            assessment = _latest_usable(session, profile_id)
        elif payload.target_basis_source == TargetBasisSource.DAILY_PLAN:
            if day.source_daily_plan is None:
                raise error(
                    "CONSUMPTION_TARGET_BASIS_INVALID",
                    "Der Tag ist mit keinem Tagesplan verknüpft.",
                    409,
                )
            assessment = day.source_daily_plan.assessment
            adjustment = day.source_daily_plan.training_day_adjustment
        day.assessment_id = None if assessment is None else assessment.id
        day.training_day_adjustment_id = None if adjustment is None else adjustment.id
        day.target_basis_source = payload.target_basis_source.value
        day.target_basis_snapshot = _basis_snapshot(assessment, adjustment)
    day.version += 1
    session.commit()
    session.expire_all()
    return detail(require_day(session, profile_id, day.id))


def link_daily_plan(
    session: Session,
    profile_id: UUID,
    day_id: UUID,
    payload: LinkDailyPlan,
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day, payload.expected_version)
    plan = plan_repository.get(session, profile_id, payload.daily_plan_id)
    if plan is None or plan.plan_date != day.consumption_date:
        raise error(
            "CONSUMPTION_PLAN_NOT_FOUND",
            "Für diesen Verzehrtag wurde kein passender Tagesplan gefunden.",
            404,
        )
    has_conflict = bool(day.source_daily_plan_id and day.source_daily_plan_id != plan.id)
    has_conflict = has_conflict or bool(day.outcomes)
    if has_conflict and not payload.confirm_conflicts:
        raise error(
            "CONSUMPTION_OUTCOME_CONFLICT",
            "Bestehende Planentscheidungen bleiben erhalten. Bitte prüfe und "
            "bestätige die Verknüpfung.",
            409,
        )
    day.source_daily_plan_id = plan.id
    linked_meals = {meal.source_plan_meal_id for meal in day.meals}
    for plan_meal in plan.meals:
        if plan_meal.id in linked_meals:
            continue
        day.meals.append(
            ConsumptionMeal(
                meal_type=plan_meal.meal_type,
                custom_name=plan_meal.custom_name,
                consumed_time=plan_meal.planned_time,
                position=len(day.meals),
                source_plan_meal_id=plan_meal.id,
                source_plan_meal_name_snapshot=(
                    plan_meal.custom_name or MEAL_LABELS_DE[MealType(plan_meal.meal_type)]
                ),
            )
        )
    day.version += 1
    session.commit()
    return detail(require_day(session, profile_id, day.id))


def add_meal(
    session: Session, profile_id: UUID, day_id: UUID, payload: MealWrite
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day)
    position = payload.position if payload.position is not None else len(day.meals)
    meal = ConsumptionMeal(
        consumption_day_id=day.id,
        meal_type=payload.meal_type.value,
        custom_name=payload.custom_name,
        consumed_time=payload.consumed_time,
        position=position,
        note=payload.note,
    )
    session.add(meal)
    day.version += 1
    session.commit()
    return _meal_dict(meal)


def _meal(day: ConsumptionDay, meal_id: UUID) -> ConsumptionMeal:
    item = next((m for m in day.meals if m.id == meal_id), None)
    if item is None:
        raise error("CONSUMPTION_MEAL_NOT_FOUND", "Die Mahlzeit wurde nicht gefunden.", 404)
    return item


def update_meal(
    session: Session, profile_id: UUID, day_id: UUID, meal_id: UUID, payload: MealWrite
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day)
    meal = _meal(day, meal_id)
    meal.meal_type, meal.custom_name, meal.consumed_time, meal.note = (
        payload.meal_type.value,
        payload.custom_name,
        payload.consumed_time,
        payload.note,
    )
    if payload.position is not None:
        meal.position = payload.position
    day.version += 1
    session.commit()
    return _meal_dict(meal)


def delete_meal(
    session: Session, profile_id: UUID, day_id: UUID, meal_id: UUID, confirm: bool
) -> dict[str, bool]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day)
    meal = _meal(day, meal_id)
    if meal.entries and not confirm:
        raise error(
            "CONSUMPTION_MEAL_NOT_EMPTY",
            "Die Mahlzeit enthält Einträge. Bitte bestätige das dauerhafte Löschen.",
            409,
        )
    session.delete(meal)
    day.version += 1
    session.commit()
    return {"deleted": True}


def reorder_meals(
    session: Session, profile_id: UUID, day_id: UUID, payload: ReorderMeals
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day, payload.expected_version)
    if set(payload.meal_ids) != {m.id for m in day.meals}:
        raise error(
            "CONSUMPTION_MEAL_REORDER_INVALID", "Die Mahlzeitenliste ist nicht vollständig."
        )
    by_id = {m.id: m for m in day.meals}
    for pos, item_id in enumerate(payload.meal_ids):
        by_id[item_id].position = pos
    day.version += 1
    session.commit()
    return detail(require_day(session, profile_id, day.id))


def _source_input(
    session: Session, profile_id: UUID, payload: EntryWrite, allow_archived: bool = False
) -> tuple[Any, Any]:
    if payload.entry_type == EntryType.FOOD:
        food = food_repository.get_food(session, profile_id, cast(UUID, payload.food_id))
        if food is None:
            raise error("CONSUMPTION_FOOD_NOT_FOUND", "Das Lebensmittel wurde nicht gefunden.", 404)
        if food.is_archived and not allow_archived:
            raise error(
                "CONSUMPTION_FOOD_ARCHIVED",
                "Archivierte Lebensmittel können nicht neu erfasst werden.",
                409,
            )
        normalized_input = cast(Decimal, payload.entered_quantity)
        normalized_unit = payload.entered_unit_code
        if normalized_unit == "kg":
            normalized_input *= Decimal(1000)
            normalized_unit = "g"
        elif normalized_unit == "l":
            normalized_input *= Decimal(1000)
            normalized_unit = "ml"
        model = MealEntry(
            entry_type="food",
            food=food,
            food_id=food.id,
            food_quantity=normalized_input,
            food_unit_code=normalized_unit,
            food_measure_id=payload.food_measure_id,
            position=0,
        )
        return _entry_input(model, 0, {}), food
    if payload.entry_type == EntryType.RECIPE:
        recipe = recipe_repository.get(session, profile_id, cast(UUID, payload.recipe_id))
        if recipe is None:
            raise error("CONSUMPTION_RECIPE_NOT_FOUND", "Das Rezept wurde nicht gefunden.", 404)
        if recipe.is_archived and not allow_archived:
            raise error(
                "CONSUMPTION_RECIPE_ARCHIVED",
                "Archivierte Rezepte können nicht neu erfasst werden.",
                409,
            )
        model = MealEntry(
            entry_type="recipe",
            recipe=recipe,
            recipe_id=recipe.id,
            recipe_portion_count=payload.recipe_portion_count,
            position=0,
        )
        return _entry_input(model, 0, {}), recipe
    return None, None


def preview_entry(
    session: Session, profile_id: UUID, day_id: UUID, payload: EntryWrite
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id)
    _open(day)
    _meal(day, payload.meal_id)
    source, _ = _source_input(session, profile_id, payload)
    if source is None:
        return {
            "entry_type": "manual_unresolved",
            "nutrients": [],
            "warnings": [
                _warning(
                    "CONSUMPTION_MANUAL_ENTRY_UNRESOLVED",
                    "Manueller Eintrag ohne Nährwertberechnung.",
                )
            ],
        }
    return {
        "entry_type": source.entry_type,
        "normalized_quantity": source.normalized_quantity,
        "normalized_unit": source.normalized_unit,
        "nutrients": [
            {
                "nutrient_code": n.nutrient_code,
                "amount": n.amount,
                "unit": n.unit,
                "complete": n.known_count == n.relevant_count,
            }
            for n in source.nutrients
        ],
        "warnings": list(source.warnings),
    }


def create_entry(
    session: Session,
    profile_id: UUID,
    day_id: UUID,
    payload: EntryWrite,
    *,
    outcome: PlannedEntryConsumptionOutcome | None = None,
    allow_archived: bool = False,
    commit: bool = True,
    entry_id: UUID | None = None,
    version: int = 1,
) -> ConsumptionEntry:
    existing = session.scalar(
        select(ConsumptionEntry).where(
            ConsumptionEntry.owner_profile_id == profile_id,
            ConsumptionEntry.client_operation_id == payload.client_operation_id,
        )
    )
    if existing is not None:
        return existing
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day, payload.expected_version)
    meal = _meal(day, payload.meal_id)
    source, model = _source_input(session, profile_id, payload, allow_archived)
    display = (payload.manual_name or "").strip() if source is None else source.source_name
    measure = (
        None
        if model is None or payload.food_measure_id is None
        else next((item for item in model.measures if item.id == payload.food_measure_id), None)
    )
    metadata = {
        "source_id": None if model is None else str(model.id),
        "source_type": payload.entry_type.value,
        "source_name": display,
        "source_archived_at_logging": False if model is None else bool(model.is_archived),
        "calculated_at": datetime.now(UTC).isoformat(),
    }
    if payload.entry_type == EntryType.FOOD and model is not None:
        metadata.update(
            {
                "brand": model.brand,
                "reference_unit": model.reference_unit,
                "density_g_per_ml": None
                if model.density_g_per_ml is None
                else str(model.density_g_per_ml),
                "measure": None
                if measure is None
                else {
                    "id": str(measure.id),
                    "name": measure.name,
                    "equivalent_quantity": str(measure.equivalent_quantity),
                    "equivalent_unit": measure.equivalent_unit,
                    "is_estimated": measure.is_estimated,
                },
            }
        )
    elif payload.entry_type == EntryType.RECIPE and model is not None:
        metadata["recipe_servings"] = str(model.servings)
    entry = ConsumptionEntry(
        id=entry_id or uuid4(),
        consumption_meal_id=meal.id,
        owner_profile_id=profile_id,
        outcome=outcome,
        entry_type=payload.entry_type.value,
        origin_type=payload.origin_type.value,
        food_id=payload.food_id,
        recipe_id=payload.recipe_id,
        manual_name=(payload.manual_name or "").strip() or None,
        source_display_name_snapshot=display,
        source_version_snapshot=None if model is None else model.updated_at.isoformat(),
        source_metadata_snapshot=metadata,
        entered_quantity=payload.entered_quantity,
        entered_unit_code=payload.entered_unit_code,
        entered_unit_label=payload.entered_unit_label,
        food_measure_id=payload.food_measure_id,
        normalized_quantity=None if source is None else source.normalized_quantity,
        normalized_unit=None if source is None else source.normalized_unit,
        recipe_portion_count=payload.recipe_portion_count,
        conversion_estimated=False if source is None else source.conversion_is_estimated,
        nutrient_snapshot_status="unresolved"
        if source is None
        else (
            "complete"
            if all(n.known_count == n.relevant_count for n in source.nutrients)
            else "partial"
        ),
        position=len(meal.entries),
        note=payload.note,
        client_operation_id=payload.client_operation_id,
        version=version,
    )
    session.add(entry)
    session.flush()
    by_code = {} if source is None else {n.nutrient_code: n for n in source.nutrients}
    for code in sorted(set(CORE_CODES) | set(by_code)):
        nutrient = by_code.get(code)
        amount = None if nutrient is None or nutrient.known_count == 0 else nutrient.amount
        state = (
            SnapshotState.UNKNOWN
            if amount is None
            else (SnapshotState.TRUE_ZERO if amount == 0 else SnapshotState.KNOWN)
        )
        definition = NUTRIENT_BY_CODE[code]
        entry.nutrient_snapshots.append(
            ConsumptionEntryNutrientSnapshot(
                nutrient_code=code,
                amount=amount,
                canonical_unit=definition.canonical_unit,
                value_state=state.value,
                source_quality="estimated" if entry.conversion_estimated else "reported",
            )
        )
    day.version += 1
    if commit:
        session.commit()
    return entry


def update_entry(
    session: Session, profile_id: UUID, day_id: UUID, entry_id: UUID, payload: EntryWrite
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day)
    old = next((e for m in day.meals for e in m.entries if e.id == entry_id), None)
    if old is None:
        raise error("CONSUMPTION_ENTRY_NOT_FOUND", "Der Eintrag wurde nicht gefunden.", 404)
    if payload.expected_version != old.version:
        raise error(
            "CONSUMPTION_CONCURRENT_MODIFICATION",
            "Der Eintrag wurde zwischenzeitlich geändert.",
            409,
        )
    outcome = old.outcome
    session.delete(old)
    session.flush()
    replacement_payload = payload.model_copy(update={"expected_version": None})
    new = create_entry(
        session,
        profile_id,
        day_id,
        replacement_payload,
        outcome=outcome,
        commit=True,
        entry_id=entry_id,
        version=old.version + 1,
    )
    return _entry_dict(new)


def delete_entry(
    session: Session, profile_id: UUID, day_id: UUID, entry_id: UUID
) -> dict[str, bool]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day)
    item = next((e for m in day.meals for e in m.entries if e.id == entry_id), None)
    if item is None:
        raise error("CONSUMPTION_ENTRY_NOT_FOUND", "Der Eintrag wurde nicht gefunden.", 404)
    session.delete(item)
    day.version += 1
    session.commit()
    return {"deleted": True}


def _plan_entry(day: ConsumptionDay, plan_entry_id: UUID) -> tuple[Any, Any]:
    plan = day.source_daily_plan
    if plan is None:
        return None, None
    for meal in plan.meals:
        for entry in meal.entries:
            if entry.id == plan_entry_id:
                return meal, entry
    return None, None


def preview_outcome(
    session: Session, profile_id: UUID, day_id: UUID, plan_entry_id: UUID, payload: OutcomeWrite
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id)
    _open(day)
    _meal_source, entry = _plan_entry(day, plan_entry_id)
    if entry is None:
        raise error(
            "CONSUMPTION_PLAN_ENTRY_NOT_FOUND", "Der Planeintrag wurde nicht gefunden.", 404
        )
    return {
        "outcome_type": payload.outcome_type,
        "source_display_name": entry.food.name if entry.entry_type == "food" else entry.recipe.name,
        "actual_entry_count": 0
        if payload.outcome_type == OutcomeType.SKIPPED
        else max(1, len(payload.actual_entries)),
        "warnings": [],
    }


def apply_outcome(
    session: Session,
    profile_id: UUID,
    day_id: UUID,
    plan_entry_id: UUID,
    payload: OutcomeWrite,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    existing = session.scalar(
        select(PlannedEntryConsumptionOutcome).where(
            PlannedEntryConsumptionOutcome.owner_profile_id == profile_id,
            PlannedEntryConsumptionOutcome.client_operation_id == payload.client_operation_id,
        )
    )
    if existing is not None:
        return _outcome_dict(existing)
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day, payload.expected_day_version)
    if any(o.source_plan_entry_id == plan_entry_id for o in day.outcomes):
        raise error(
            "CONSUMPTION_PLAN_ENTRY_ALREADY_RESOLVED",
            "Der Planeintrag wurde bereits bearbeitet.",
            409,
        )
    plan_meal, planned = _plan_entry(day, plan_entry_id)
    if planned is None:
        raise error(
            "CONSUMPTION_PLAN_ENTRY_NOT_FOUND", "Der Planeintrag wurde nicht gefunden.", 404
        )
    name = planned.food.name if planned.entry_type == "food" else planned.recipe.name
    outcome = PlannedEntryConsumptionOutcome(
        consumption_day_id=day.id,
        owner_profile_id=profile_id,
        source_daily_plan_id=day.source_daily_plan_id,
        source_plan_meal_id=plan_meal.id,
        source_plan_entry_id=planned.id,
        source_plan_entry_type_snapshot=planned.entry_type,
        source_display_name_snapshot=name,
        planned_quantity_snapshot=planned.food_quantity,
        planned_unit_snapshot=planned.food_unit_code,
        planned_recipe_portions_snapshot=planned.recipe_portion_count,
        source_version_snapshot=(
            planned.food.updated_at if planned.entry_type == "food" else planned.recipe.updated_at
        ).isoformat(),
        source_plan_entry_updated_at_snapshot=planned.updated_at.isoformat(),
        outcome_type=payload.outcome_type.value,
        client_operation_id=payload.client_operation_id,
        note=payload.note,
    )
    session.add(outcome)
    session.flush()
    writes = list(payload.actual_entries)
    if payload.outcome_type == OutcomeType.AS_PLANNED:
        meal = next((m for m in day.meals if m.source_plan_meal_id == plan_meal.id), None)
        if meal is None:
            raise error("CONSUMPTION_MEAL_NOT_FOUND", "Die übernommene Planmahlzeit fehlt.", 409)
        writes = [
            EntryWrite(
                meal_id=meal.id,
                entry_type=EntryType(planned.entry_type),
                origin_type=OriginType.PLANNED,
                food_id=planned.food_id,
                recipe_id=planned.recipe_id,
                entered_quantity=planned.food_quantity,
                entered_unit_code=planned.food_unit_code,
                food_measure_id=planned.food_measure_id,
                recipe_portion_count=planned.recipe_portion_count,
                client_operation_id=uuid4(),
            )
        ]
    if payload.outcome_type not in {OutcomeType.SKIPPED, OutcomeType.AS_PLANNED} and not writes:
        raise error(
            "CONSUMPTION_REPLACEMENT_REQUIRED",
            "Bitte erfasse mindestens einen tatsächlichen Eintrag.",
        )
    for write in writes:
        write.origin_type = (
            OriginType.REPLACEMENT
            if payload.outcome_type == OutcomeType.REPLACED
            else OriginType.PLANNED
        )
        create_entry(
            session,
            profile_id,
            day.id,
            write,
            outcome=outcome,
            allow_archived=payload.outcome_type == OutcomeType.AS_PLANNED,
            commit=False,
        )
    day.version += 1
    if commit:
        session.commit()
    return _outcome_dict(outcome)


def confirm_whole_meal(
    session: Session,
    profile_id: UUID,
    day_id: UUID,
    plan_meal_id: UUID,
    payload: ConfirmWholeMeal,
) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day, payload.expected_day_version)
    if day.source_daily_plan is None:
        raise error(
            "CONSUMPTION_PLAN_NOT_FOUND", "Der Verzehrtag ist mit keinem Tagesplan verknüpft.", 409
        )
    plan_meal = next((m for m in day.source_daily_plan.meals if m.id == plan_meal_id), None)
    if plan_meal is None:
        raise error(
            "CONSUMPTION_PLAN_ENTRY_NOT_FOUND", "Die Planmahlzeit wurde nicht gefunden.", 404
        )
    pending = [
        entry
        for entry in plan_meal.entries
        if not any(outcome.source_plan_entry_id == entry.id for outcome in day.outcomes)
    ]
    if not pending:
        return {"applied_count": 0, "day": detail(day)}
    for entry in pending:
        operation_id = uuid5(payload.client_operation_id, str(entry.id))
        apply_outcome(
            session,
            profile_id,
            day.id,
            entry.id,
            OutcomeWrite(
                outcome_type=OutcomeType.AS_PLANNED,
                client_operation_id=operation_id,
                expected_day_version=day.version,
            ),
            commit=False,
        )
    session.commit()
    session.expire_all()
    return {"applied_count": len(pending), "day": detail(require_day(session, profile_id, day.id))}


def delete_outcome(
    session: Session, profile_id: UUID, day_id: UUID, plan_entry_id: UUID, confirm: bool
) -> dict[str, bool]:
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day)
    outcome = next((o for o in day.outcomes if o.source_plan_entry_id == plan_entry_id), None)
    if outcome is None:
        raise error(
            "CONSUMPTION_PLAN_ENTRY_NOT_FOUND",
            "Es besteht keine Entscheidung für diesen Planeintrag.",
            404,
        )
    if outcome.entries and not confirm:
        raise error(
            "CONSUMPTION_OUTCOME_CONFLICT",
            "Bitte bestätige das Löschen der verknüpften Verzehreinträge.",
            409,
        )
    session.delete(outcome)
    day.version += 1
    session.commit()
    return {"deleted": True}


def finalize(
    session: Session, profile_id: UUID, day_id: UUID, payload: FinalizeWrite
) -> dict[str, Any]:
    existing = repository.get(session, profile_id, day_id)
    if existing is not None and existing.finalization_operation_id == payload.client_operation_id:
        return detail(existing)
    if payload.completeness_attestation == Completeness.NOT_DECLARED:
        raise error(
            "CONSUMPTION_FINALIZATION_CONFIRMATION_REQUIRED",
            "Bitte beschreibe die Vollständigkeit der Aufzeichnung.",
        )
    day = require_day(session, profile_id, day_id, lock=True)
    _open(day, payload.expected_version)
    quality = _quality(day)
    if quality["warnings"] and not payload.confirm_warnings:
        raise error(
            "CONSUMPTION_FINALIZATION_CONFIRMATION_REQUIRED",
            "Bitte prüfe und bestätige die Hinweise vor dem Abschluss.",
            409,
        )
    day.status, day.completeness_attestation, day.finalized_at = (
        DayStatus.FINALIZED.value,
        payload.completeness_attestation.value,
        datetime.now(UTC),
    )
    day.finalization_operation_id = payload.client_operation_id
    day.version += 1
    session.commit()
    return detail(require_day(session, profile_id, day.id))


def reopen(session: Session, profile_id: UUID, day_id: UUID) -> dict[str, Any]:
    day = require_day(session, profile_id, day_id, lock=True)
    day.status, day.completeness_attestation, day.finalized_at = (
        DayStatus.OPEN.value,
        Completeness.NOT_DECLARED.value,
        None,
    )
    day.finalization_operation_id = None
    day.version += 1
    session.commit()
    return detail(require_day(session, profile_id, day.id))


def delete_day(session: Session, profile_id: UUID, day_id: UUID) -> dict[str, bool]:
    day = require_day(session, profile_id, day_id, lock=True)
    session.delete(day)
    session.commit()
    return {"deleted": True}


def _totals_for_entries(entries: list[ConsumptionEntry]) -> list[dict[str, Any]]:
    codes = set(CORE_CODES) | {s.nutrient_code for e in entries for s in e.nutrient_snapshots}
    out: list[dict[str, Any]] = []
    for code in sorted(codes, key=lambda c: NUTRIENT_BY_CODE[c].display_order):
        snapshots = [s for e in entries for s in e.nutrient_snapshots if s.nutrient_code == code]
        known = sum(s.amount is not None for s in snapshots)
        relevant = len(entries)
        amount = (
            sum((s.amount for s in snapshots if s.amount is not None), Decimal(0))
            if known
            else None
        )
        definition = NUTRIENT_BY_CODE[code]
        out.append(
            {
                "nutrient_code": code,
                "display_name_de": definition.display_name_de,
                "category": definition.category,
                "amount": amount,
                "unit": definition.canonical_unit,
                "known_component_count": known,
                "relevant_component_count": relevant,
                "coverage_ratio": Decimal(known) / Decimal(relevant) if relevant else None,
                "is_complete": relevant > 0 and known == relevant,
                "missing_sources": [],
            }
        )
    return out


def _totals(day: ConsumptionDay) -> list[dict[str, Any]]:
    return _totals_for_entries([e for m in day.meals for e in m.entries])


def _quality(day: ConsumptionDay) -> dict[str, Any]:
    entries = [e for m in day.meals for e in m.entries]
    plan_entries = (
        []
        if day.source_daily_plan is None
        else [e for m in day.source_daily_plan.meals for e in m.entries]
    )
    pending = len(
        [e for e in plan_entries if not any(o.source_plan_entry_id == e.id for o in day.outcomes)]
    )
    unresolved = sum(e.entry_type == EntryType.MANUAL for e in entries)
    current_by_id = {e.id: e for e in plan_entries}
    source_changed = 0
    for outcome in day.outcomes:
        current = (
            None
            if outcome.source_plan_entry_id is None
            else current_by_id.get(outcome.source_plan_entry_id)
        )
        if current is None:
            source_changed += 1
            continue
        source = current.food if current.entry_type == "food" else current.recipe
        if (
            source is None
            or source.updated_at.isoformat() != outcome.source_version_snapshot
            or current.updated_at.isoformat() != outcome.source_plan_entry_updated_at_snapshot
        ):
            source_changed += 1
    totals = _totals(day)
    energy = next((t for t in totals if t["nutrient_code"] == "energy_kcal"), None)
    warnings = []
    if pending:
        warnings.append(
            _warning(
                "CONSUMPTION_PLAN_ENTRY_PENDING", f"{pending} geplante Einträge sind noch offen."
            )
        )
    if unresolved:
        warnings.append(
            _warning(
                "CONSUMPTION_MANUAL_ENTRY_UNRESOLVED",
                "Mindestens ein Eintrag wurde ohne Nährwertberechnung erfasst.",
            )
        )
    if energy and not energy["is_complete"]:
        warnings.append(
            _warning(
                "CONSUMPTION_NUTRIENT_DATA_INCOMPLETE",
                "Die bekannten Nährwerte sind nur eine Untergrenze.",
            )
        )
    if source_changed:
        warnings.append(
            _warning(
                "CONSUMPTION_PLAN_SOURCE_CHANGED",
                "Mindestens ein bereits entschiedener Planeintrag wurde später geändert "
                "oder entfernt.",
            )
        )
    return {
        "status": day.status,
        "completeness_attestation": day.completeness_attestation,
        "planned_entry_count": len(plan_entries),
        "pending_plan_entry_count": pending,
        "confirmed_plan_entry_count": len(day.outcomes),
        "skipped_plan_entry_count": sum(
            o.outcome_type == OutcomeType.SKIPPED for o in day.outcomes
        ),
        "replaced_plan_entry_count": sum(
            o.outcome_type == OutcomeType.REPLACED for o in day.outcomes
        ),
        "unplanned_entry_count": sum(e.origin_type == OriginType.UNPLANNED for e in entries),
        "unresolved_entry_count": unresolved,
        "estimated_conversion_count": sum(e.conversion_estimated for e in entries),
        "source_changed_count": source_changed,
        "basic_nutrition_complete": all(
            t["is_complete"] for t in totals if t["nutrient_code"] in CORE_CODES
        ),
        "quality_level": "empty"
        if not entries
        else (
            "finalized_complete_to_best_knowledge"
            if day.status == DayStatus.FINALIZED
            and day.completeness_attestation == Completeness.COMPLETE
            else ("finalized_partial" if day.status == DayStatus.FINALIZED else "reviewable")
        ),
        "warnings": warnings,
    }


def summary(day: ConsumptionDay) -> dict[str, Any]:
    totals = _totals(day)
    comparisons: list[dict[str, object]] = []
    targets = _targets_from_snapshot(day)
    if not targets and day.assessment is not None:
        targets = extract_targets(day.assessment)
        if day.training_day_adjustment is not None:
            targets = _adjusted_targets(targets, day.training_day_adjustment)
    if targets:
        comparisons, _ = compare_targets(totals, targets)
    quality = _quality(day)
    energy = next((t for t in totals if t["nutrient_code"] == "energy_kcal"), None)
    readiness = (
        day.status == DayStatus.FINALIZED
        and day.completeness_attestation == Completeness.COMPLETE
        and quality["unresolved_entry_count"] == 0
        and energy is not None
        and energy["amount"] is not None
        and energy["is_complete"]
    )
    reasons = (
        []
        if readiness
        else [
            "Der Tag ist nicht abgeschlossen, nicht vollständig erklärt oder enthält "
            "unvollständige Energiedaten."
        ]
    )
    return {
        "actual_totals": totals,
        "target_comparison": comparisons,
        "quality": quality,
        "potentially_calibration_usable": readiness,
        "calibration_exclusion_reasons": reasons,
        "notices": [
            "Verzehreinträge verändern den Vorrat nicht automatisch.",
            "Die Angaben sind selbst berichtet und keine Messung der Nährstoffaufnahme.",
        ],
    }


def detail(day: ConsumptionDay) -> dict[str, Any]:
    planned: list[dict[str, Any]] = []
    current_ids: set[UUID] = set()
    if day.source_daily_plan is not None:
        for meal in day.source_daily_plan.meals:
            for entry in meal.entries:
                current_ids.add(entry.id)
                outcome = next(
                    (o for o in day.outcomes if o.source_plan_entry_id == entry.id), None
                )
                source = entry.food if entry.entry_type == "food" else entry.recipe
                planned_input = _entry_input(entry, entry.position, {})
                planned.append(
                    {
                        "id": entry.id,
                        "meal_id": meal.id,
                        "entry_type": entry.entry_type,
                        "display_name": (
                            entry.food.name
                            if entry.food is not None
                            else entry.recipe.name
                            if entry.recipe is not None
                            else "Nicht mehr verfügbare Quelle"
                        ),
                        "planned_quantity": entry.food_quantity,
                        "planned_unit": entry.food_unit_code,
                        "planned_recipe_portions": entry.recipe_portion_count,
                        "source_id": entry.food_id or entry.recipe_id,
                        "source_archived": bool(source and source.is_archived),
                        "planned_nutrients": [
                            {
                                "nutrient_code": nutrient.nutrient_code,
                                "amount": nutrient.amount
                                if nutrient.known_count == nutrient.relevant_count
                                else None,
                                "unit": nutrient.unit,
                            }
                            for nutrient in planned_input.nutrients
                        ],
                        "status": "pending" if outcome is None else outcome.outcome_type,
                        "outcome": None if outcome is None else _outcome_dict(outcome),
                        "quantity_comparison": _entry_quantity_comparison(entry, outcome),
                    }
                )
    for outcome in day.outcomes:
        if outcome.source_plan_entry_id not in current_ids:
            planned.append(
                {
                    "id": outcome.source_plan_entry_id,
                    "meal_id": outcome.source_plan_meal_id,
                    "entry_type": outcome.source_plan_entry_type_snapshot,
                    "display_name": outcome.source_display_name_snapshot,
                    "planned_quantity": outcome.planned_quantity_snapshot,
                    "planned_unit": outcome.planned_unit_snapshot,
                    "planned_recipe_portions": outcome.planned_recipe_portions_snapshot,
                    "status": outcome.outcome_type,
                    "source_unavailable": True,
                    "outcome": _outcome_dict(outcome),
                }
            )
    return {
        "id": day.id,
        "consumption_date": day.consumption_date,
        "source_daily_plan_id": day.source_daily_plan_id,
        "assessment_id": day.assessment_id,
        "training_day_adjustment_id": day.training_day_adjustment_id,
        "target_basis_source": day.target_basis_source,
        "target_basis_snapshot": day.target_basis_snapshot,
        "status": day.status,
        "completeness_attestation": day.completeness_attestation,
        "finalized_at": day.finalized_at,
        "note": day.note,
        "version": day.version,
        "created_at": day.created_at,
        "updated_at": day.updated_at,
        "meals": [_meal_dict(m) for m in sorted(day.meals, key=lambda item: item.position)],
        "planned_entries": planned,
        "summary": summary(day),
        "planned_vs_actual": planned_vs_actual(day),
    }


def _entry_quantity_comparison(
    planned: MealEntry,
    outcome: PlannedEntryConsumptionOutcome | None,
) -> dict[str, Any]:
    if outcome is None or outcome.outcome_type in {OutcomeType.SKIPPED, OutcomeType.REPLACED}:
        return {"relation": "not_comparable", "difference": None}
    entries = list(outcome.entries)
    if len(entries) != 1:
        return {"relation": "not_comparable", "difference": None}
    actual = entries[0]
    if planned.entry_type == "food" and actual.food_id == planned.food_id:
        planned_input = _entry_input(planned, planned.position, {})
        if actual.normalized_unit == planned_input.normalized_unit:
            difference = cast(Decimal, actual.normalized_quantity) - cast(
                Decimal, planned_input.normalized_quantity
            )
            return {
                "relation": "comparable",
                "difference": difference,
                "unit": actual.normalized_unit,
            }
    if planned.entry_type == "recipe" and actual.recipe_id == planned.recipe_id:
        difference = cast(Decimal, actual.recipe_portion_count) - cast(
            Decimal, planned.recipe_portion_count
        )
        return {"relation": "comparable", "difference": difference, "unit": "portion"}
    return {"relation": "not_comparable", "difference": None}


def _entry_dict(e: ConsumptionEntry) -> dict[str, Any]:
    return {
        "id": e.id,
        "meal_id": e.consumption_meal_id,
        "outcome_id": e.outcome_id,
        "entry_type": e.entry_type,
        "origin_type": e.origin_type,
        "food_id": e.food_id,
        "recipe_id": e.recipe_id,
        "manual_name": e.manual_name,
        "source_display_name_snapshot": e.source_display_name_snapshot,
        "source_version_snapshot": e.source_version_snapshot,
        "entered_quantity": e.entered_quantity,
        "entered_unit_code": e.entered_unit_code,
        "entered_unit_label": e.entered_unit_label,
        "food_measure_id": e.food_measure_id,
        "normalized_quantity": e.normalized_quantity,
        "normalized_unit": e.normalized_unit,
        "recipe_portion_count": e.recipe_portion_count,
        "conversion_estimated": e.conversion_estimated,
        "nutrient_snapshot_status": e.nutrient_snapshot_status,
        "position": e.position,
        "note": e.note,
        "version": e.version,
        "source_metadata_snapshot": e.source_metadata_snapshot,
        "nutrient_snapshots": [
            {
                "nutrient_code": s.nutrient_code,
                "amount": s.amount,
                "unit": s.canonical_unit,
                "value_state": s.value_state,
            }
            for s in e.nutrient_snapshots
        ],
    }


def _meal_dict(m: ConsumptionMeal) -> dict[str, Any]:
    entries = list(m.entries)
    return {
        "id": m.id,
        "meal_type": m.meal_type,
        "custom_name": m.custom_name,
        "meal_name": m.custom_name or MEAL_LABELS_DE[MealType(m.meal_type)],
        "consumed_time": m.consumed_time,
        "position": m.position,
        "source_plan_meal_id": m.source_plan_meal_id,
        "note": m.note,
        "entries": [_entry_dict(e) for e in entries],
        "nutrient_totals": _totals_for_entries(entries),
        "unresolved_entry_count": sum(e.entry_type == EntryType.MANUAL for e in entries),
        "planned_outcome_summary": {
            "resolved": len({e.outcome_id for e in entries if e.outcome_id is not None}),
            "unplanned_entries": sum(e.origin_type == OriginType.UNPLANNED for e in entries),
        },
    }


def _outcome_dict(o: PlannedEntryConsumptionOutcome) -> dict[str, Any]:
    return {
        "id": o.id,
        "source_plan_entry_id": o.source_plan_entry_id,
        "source_display_name_snapshot": o.source_display_name_snapshot,
        "outcome_type": o.outcome_type,
        "decided_at": o.decided_at,
        "entries": [_entry_dict(e) for e in o.entries],
    }


def _warning(code: str, explanation: str) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "warning",
        "explanation_de": explanation,
        "suggested_action_de": "Bitte prüfe die Aufzeichnung.",
    }


def history(
    session: Session,
    profile_id: UUID,
    date_from: date | None,
    date_to: date | None,
    status: str | None,
    completeness: str | None,
    has_daily_plan: bool | None,
    has_unresolved_entries: bool | None,
    page: int,
    page_size: int,
    sort: str = "date_desc",
) -> dict[str, Any]:
    items, total = repository.list_days(
        session,
        profile_id,
        date_from,
        date_to,
        status,
        completeness,
        has_daily_plan,
        has_unresolved_entries,
        page,
        page_size,
        sort,
    )
    return {
        "items": [_history_item(d) for d in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def _history_item(day: ConsumptionDay) -> dict[str, Any]:
    result = summary(day)
    energy = next(
        (item for item in result["actual_totals"] if item["nutrient_code"] == "energy_kcal"),
        None,
    )
    target = next(
        (item for item in result["target_comparison"] if item["nutrient_code"] == "energy_kcal"),
        None,
    )
    plan = planned_vs_actual(day)
    planned_energy = next(
        (item for item in plan["differences"] if item["nutrient_code"] == "energy_kcal"),
        None,
    )
    return {
        "id": day.id,
        "consumption_date": day.consumption_date,
        "status": day.status,
        "completeness_attestation": day.completeness_attestation,
        "entry_count": sum(len(m.entries) for m in day.meals),
        "actual_energy_kcal": None if energy is None else energy["amount"],
        "actual_energy_complete": False if energy is None else energy["is_complete"],
        "target_relation": None if target is None else target.get("relation"),
        "planned_actual_relation": None
        if planned_energy is None
        else planned_energy.get("relation"),
        "planned_actual_difference_kcal": None
        if planned_energy is None
        else planned_energy.get("difference"),
        "unresolved_entry_count": result["quality"]["unresolved_entry_count"],
        "has_daily_plan": day.source_daily_plan_id is not None,
        "updated_at": day.updated_at,
    }


def weekly(session: Session, profile_id: UUID, week_start: date) -> dict[str, Any]:
    start = week_start - timedelta(days=week_start.weekday())
    end = start + timedelta(days=6)
    days, _ = repository.list_days(
        session, profile_id, start, end, None, None, None, None, 1, 7, "date_asc"
    )
    complete = [d for d in days if d.completeness_attestation == Completeness.COMPLETE]
    energy = [
        next((t["amount"] for t in _totals(d) if t["nutrient_code"] == "energy_kcal"), None)
        for d in days
    ]
    known = [e for e in energy if e is not None]
    nutrient_codes = {item["nutrient_code"] for day in days for item in _totals(day)}
    nutrient_totals: list[dict[str, Any]] = []
    for code in sorted(nutrient_codes, key=lambda item: NUTRIENT_BY_CODE[item].display_order):
        values = [
            next((item for item in _totals(day) if item["nutrient_code"] == code), None)
            for day in days
        ]
        known_values = [item for item in values if item is not None and item["amount"] is not None]
        amount = (
            sum((cast(Decimal, item["amount"]) for item in known_values), Decimal(0))
            if known_values
            else None
        )
        nutrient_totals.append(
            {
                "nutrient_code": code,
                "amount": amount,
                "unit": NUTRIENT_BY_CODE[code].canonical_unit,
                "known_day_count": len(known_values),
                "recorded_day_count": len(days),
                "is_complete": len(known_values) == len(days) and bool(days),
                "average_per_recorded_day": amount / len(days)
                if amount is not None and days
                else None,
                "average_per_complete_attestation_day": amount / len(complete)
                if amount is not None and complete
                else None,
            }
        )
    return {
        "week_start": start,
        "week_end": end,
        "calendar_day_count": 7,
        "recorded_day_count": len(days),
        "finalized_day_count": sum(d.status == DayStatus.FINALIZED for d in days),
        "complete_attestation_day_count": len(complete),
        "partial_attestation_day_count": sum(
            d.completeness_attestation in {Completeness.PARTIAL, Completeness.UNCERTAIN}
            for d in days
        ),
        "missing_day_count": 7 - len(days),
        "known_energy_total_kcal": sum(known, Decimal(0)) if known else None,
        "average_energy_per_recorded_day_kcal": sum(known, Decimal(0)) / len(days)
        if days and known
        else None,
        "target_day_count": sum(d.assessment_id is not None for d in days),
        "unresolved_entry_count": sum(_quality(d)["unresolved_entry_count"] for d in days),
        "nutrient_totals": nutrient_totals,
        "days": [
            {
                "date": start + timedelta(days=i),
                "recorded": any(d.consumption_date == start + timedelta(days=i) for d in days),
                "status": next(
                    (d.status for d in days if d.consumption_date == start + timedelta(days=i)),
                    None,
                ),
                "completeness_attestation": next(
                    (
                        d.completeness_attestation
                        for d in days
                        if d.consumption_date == start + timedelta(days=i)
                    ),
                    None,
                ),
                "actual_energy_kcal": next(
                    (
                        next(
                            (
                                item["amount"]
                                for item in _totals(d)
                                if item["nutrient_code"] == "energy_kcal"
                            ),
                            None,
                        )
                        for d in days
                        if d.consumption_date == start + timedelta(days=i)
                    ),
                    None,
                ),
                "target_comparison": next(
                    (
                        summary(d)["target_comparison"]
                        for d in days
                        if d.consumption_date == start + timedelta(days=i)
                    ),
                    [],
                ),
            }
            for i in range(7)
        ],
    }


def planned_vs_actual(day: ConsumptionDay) -> dict[str, Any]:
    actual = _totals(day)
    if day.source_daily_plan is None:
        return {
            "planned_totals": [],
            "actual_totals": actual,
            "differences": [],
            "relation": "no_plan",
            "outcome_counts": _quality(day),
        }
    planned_response = plan_service.serialize(day.source_daily_plan)
    planned = [item.model_dump() for item in planned_response.daily_totals]
    actual_by_code = {item["nutrient_code"]: item for item in actual}
    differences: list[dict[str, Any]] = []
    for planned_item in planned:
        actual_item = actual_by_code.get(planned_item["nutrient_code"])
        comparable = (
            planned_item["amount"] is not None
            and actual_item is not None
            and actual_item["amount"] is not None
            and planned_item["unit"] == actual_item["unit"]
            and planned_item["is_complete"]
            and actual_item["is_complete"]
        )
        differences.append(
            {
                "nutrient_code": planned_item["nutrient_code"],
                "planned_amount": planned_item["amount"],
                "actual_amount": None if actual_item is None else actual_item["amount"],
                "unit": planned_item["unit"],
                "difference": (
                    cast(Decimal, actual_item["amount"]) - cast(Decimal, planned_item["amount"])
                    if comparable and actual_item is not None
                    else None
                ),
                "relation": "comparable" if comparable else "indeterminate",
            }
        )
    return {
        "planned_totals": planned,
        "actual_totals": actual,
        "differences": differences,
        "relation": "descriptive",
        "outcome_counts": _quality(day),
    }
