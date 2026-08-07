# ruff: noqa: E501
# mypy: disable-error-code="no-any-return"
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.modules.consumption_tracking import service as consumption_service
from app.modules.consumption_tracking.models import (
    ConsumptionEntry,
    ConsumptionRecipeIngredientSnapshot,
)
from app.modules.foods import repository as food_repository
from app.modules.pantry import service as pantry_service
from app.modules.pantry.models import PantryLocation, PantryMovement, PantryStockLot
from app.modules.pantry.schemas import QuantityOperation

from . import engine
from .models import (
    PantryConsumptionAllocation,
    PantryConsumptionReconciliationBatch,
    PantryConsumptionRequirement,
    PantryConsumptionReversal,
    PantryConsumptionReversalAllocation,
)
from .schemas import (
    ApplyRequest,
    DayDeletionResolution,
    EntryDecision,
    EntryDeletionResolution,
    PreviewRequest,
    RequirementDecision,
    ReversalApplyRequest,
    ReversalPreviewRequest,
    ReversalSelection,
)

RULE_VERSION = "pantry-consumption-reconciliation/1.0"


def error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code, message, status)


def _json(value: object) -> Any:
    return jsonable_encoder(value, custom_encoder={Decimal: str})


def _token(body: dict[str, Any]) -> str:
    stable = {
        key: value for key, value in body.items() if key not in {"preview_token", "calculated_at"}
    }
    canonical = json.dumps(_json(stable), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _entries(day: Any) -> dict[UUID, ConsumptionEntry]:
    return {entry.id: entry for meal in day.meals for entry in meal.entries}


def _active_quantity(
    session: Session, entry_id: UUID, snapshot_id: UUID | None, food_id: UUID | None
) -> tuple[Decimal, Decimal, set[str]]:
    requirements = list(
        session.scalars(
            select(PantryConsumptionRequirement)
            .join(PantryConsumptionReconciliationBatch)
            .where(
                PantryConsumptionRequirement.consumption_entry_id == entry_id,
                PantryConsumptionReconciliationBatch.status.in_(("active", "partially_reversed")),
                PantryConsumptionRequirement.recipe_ingredient_snapshot_id == snapshot_id,
                PantryConsumptionRequirement.food_id == food_id,
            )
            .options(
                selectinload(PantryConsumptionRequirement.allocations).selectinload(
                    PantryConsumptionAllocation.reversal_allocations
                )
            )
        )
    )
    allocated = sum(
        (
            allocation.allocated_quantity
            for requirement in requirements
            for allocation in requirement.allocations
        ),
        Decimal(0),
    )
    reversed_quantity = sum(
        (
            reversal.reversal_quantity
            for requirement in requirements
            for allocation in requirement.allocations
            for reversal in allocation.reversal_allocations
        ),
        Decimal(0),
    )
    return (
        allocated - reversed_quantity,
        reversed_quantity,
        {item.source_context for item in requirements},
    )


def _lots(session: Session, owner: UUID, food_ids: set[UUID]) -> dict[UUID, list[PantryStockLot]]:
    if not food_ids:
        return {}
    rows = list(
        session.scalars(
            select(PantryStockLot)
            .join(PantryLocation)
            .where(
                PantryStockLot.owner_profile_id == owner,
                PantryStockLot.food_id.in_(food_ids),
                PantryStockLot.is_archived.is_(False),
                PantryStockLot.is_depleted.is_(False),
                PantryStockLot.current_quantity > 0,
                PantryLocation.is_archived.is_(False),
            )
            .options(selectinload(PantryStockLot.location), selectinload(PantryStockLot.food))
        )
    )
    grouped: dict[UUID, list[PantryStockLot]] = {}
    for lot in rows:
        grouped.setdefault(lot.food_id, []).append(lot)
    return grouped


def _lot_payload(lot: PantryStockLot, allocated: Decimal = Decimal(0)) -> dict[str, Any]:
    status = pantry_service.date_status(lot)
    return {
        "stock_lot_id": str(lot.id),
        "food_id": str(lot.food_id),
        "location_id": str(lot.location_id),
        "location_name": lot.location.name,
        "available_quantity": lot.current_quantity,
        "allocated_quantity": allocated,
        "canonical_unit": lot.normalized_unit,
        "date_status": status,
        "relevant_date": lot.use_by_date or lot.best_before_date,
        "version": lot.version,
        "is_suggested": allocated > 0,
    }


def _warning(code: str, explanation: str, *, affected: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "warning",
        "explanation_de": explanation,
        "affected": affected,
        "suggested_action_de": "Bitte prüfen und ausdrücklich entscheiden.",
    }


def _decision_for(
    snapshot_id: UUID, decisions: list[RequirementDecision]
) -> RequirementDecision | None:
    return next(
        (
            decision
            for decision in decisions
            if decision.recipe_ingredient_snapshot_id == snapshot_id
        ),
        None,
    )


def _legacy_recipe_snapshots(
    entry: ConsumptionEntry,
) -> list[ConsumptionRecipeIngredientSnapshot] | None:
    recipe = entry.recipe
    if (
        recipe is None
        or entry.source_version_snapshot is None
        or recipe.updated_at.isoformat() != entry.source_version_snapshot
        or entry.recipe_portion_count is None
    ):
        return None
    return [
        ConsumptionRecipeIngredientSnapshot(
            id=uuid5(entry.id, str(ingredient.id)),
            consumption_entry_id=entry.id,
            source_recipe_id=recipe.id,
            source_recipe_ingredient_id=ingredient.id,
            food_id=ingredient.food_id,
            food_name_snapshot=ingredient.food.name,
            ingredient_position=ingredient.position,
            original_quantity=ingredient.quantity,
            original_unit_code=ingredient.unit_code,
            normalized_quantity_for_logged_portions=(
                ingredient.normalized_quantity * entry.recipe_portion_count / recipe.servings
            ),
            canonical_unit=ingredient.normalized_unit,
            food_measure_snapshot=None,
            conversion_estimated=ingredient.conversion_is_estimated,
            optional_ingredient=ingredient.is_optional,
            normalization_status="normalized",
            source_version_snapshot=recipe.updated_at.isoformat(),
        )
        for ingredient in recipe.ingredients
    ]


def _requirement(
    session: Session,
    entry: ConsumptionEntry,
    *,
    requirement_type: str,
    snapshot_id: UUID | None,
    food_id: UUID | None,
    food_name: str,
    required: Decimal | None,
    unit: str | None,
    estimated: bool,
    context: str,
    selected: Decimal,
    decision_allocations: list[Any],
    lots_by_food: dict[UUID, list[PantryStockLot]],
    optional: bool = False,
    normalization_status: str = "normalized",
) -> dict[str, Any]:
    active, reversed_quantity, decisions = _active_quantity(session, entry.id, snapshot_id, food_id)
    remaining = None if required is None else engine.remaining(required, active)
    if remaining is not None and selected > remaining:
        raise error(
            "PANTRY_CONSUMPTION_QUANTITY_EXCEEDS_REMAINING",
            "Die gewählte Vorratsmenge übersteigt die noch abgleichbare Menge.",
            409,
        )
    candidates = lots_by_food.get(food_id, []) if food_id else []
    candidate_by_id = {lot.id: lot for lot in candidates}
    allocations: list[dict[str, Any]] = []
    if decision_allocations:
        total = Decimal(0)
        for allocation in decision_allocations:
            lot = candidate_by_id.get(allocation.stock_lot_id)
            if lot is None:
                raise error(
                    "PANTRY_CONSUMPTION_LOT_NOT_FOUND",
                    "Eine ausgewählte Charge ist nicht verfügbar.",
                    404,
                )
            if lot.version != allocation.expected_lot_version:
                raise error(
                    "PANTRY_CONSUMPTION_PREVIEW_STALE",
                    "Ein Vorratsbestand wurde zwischenzeitlich geändert.",
                    409,
                )
            if lot.food_id != food_id or lot.normalized_unit != unit:
                raise error(
                    "PANTRY_CONSUMPTION_FOOD_MISMATCH",
                    "Charge und Anforderung passen nicht zusammen.",
                    409,
                )
            if allocation.quantity > lot.current_quantity:
                raise error(
                    "PANTRY_CONSUMPTION_INSUFFICIENT_STOCK",
                    "Der Vorratsbestand reicht nicht aus.",
                    409,
                )
            total += allocation.quantity
            allocations.append(_lot_payload(lot, allocation.quantity))
        if total != selected:
            raise error(
                "PANTRY_CONSUMPTION_ALLOCATION_MISMATCH",
                "Die Chargenmengen entsprechen nicht der gewählten Vorratsmenge.",
            )
    elif selected > 0:
        candidate_models = [
            engine.LotCandidate(
                lot.id,
                lot.current_quantity,
                lot.normalized_unit,
                pantry_service.date_status(lot),
                lot.use_by_date or lot.best_before_date,
                lot.created_at,
            )
            for lot in candidates
        ]
        suggestion, _uncovered = engine.suggest(selected, candidate_models)
        allocations = [
            _lot_payload(candidate_by_id[lot_id], quantity) for lot_id, quantity in suggestion
        ]
    allocated = sum((Decimal(str(item["allocated_quantity"])) for item in allocations), Decimal(0))
    warnings: list[dict[str, Any]] = []
    if allocated < selected:
        warnings.append(
            _warning(
                "PANTRY_CONSUMPTION_INSUFFICIENT_STOCK",
                "Der verfügbare Bestand deckt die ausgewählte Menge nicht vollständig.",
                affected=str(entry.id),
            )
        )
    if estimated:
        warnings.append(
            _warning(
                "PANTRY_CONSUMPTION_ESTIMATED_CONVERSION",
                "Die Mengen-Normalisierung enthält eine geschätzte Umrechnung.",
                affected=str(entry.id),
            )
        )
    for allocation in allocations:
        if allocation["date_status"] == "past_best_before":
            warnings.append(
                _warning(
                    "PANTRY_CONSUMPTION_PAST_BEST_BEFORE_LOT",
                    "Eine ausgewählte Charge besitzt ein überschrittenes Mindesthaltbarkeitsdatum.",
                    affected=allocation["stock_lot_id"],
                )
            )
        if allocation["date_status"] == "past_use_by":
            warnings.append(
                _warning(
                    "PANTRY_CONSUMPTION_PAST_USE_BY_LOT",
                    "Eine ausgewählte Charge besitzt ein überschrittenes Verbrauchsdatum. Daraus folgt keine Aussage zur Lebensmittelsicherheit.",
                    affected=allocation["stock_lot_id"],
                )
            )
    return {
        "requirement_key": str(snapshot_id or food_id or entry.id),
        "requirement_type": requirement_type,
        "recipe_ingredient_snapshot_id": None if snapshot_id is None else str(snapshot_id),
        "food_id": None if food_id is None else str(food_id),
        "food_name": food_name,
        "theoretical_required_quantity": required,
        "previously_reconciled_quantity": active,
        "previously_reversed_quantity": reversed_quantity,
        "remaining_reconcilable_quantity": remaining,
        "selected_pantry_quantity": selected,
        "canonical_unit": unit,
        "source_context": context,
        "optional_ingredient": optional,
        "normalization_status": normalization_status,
        "conversion_estimated": estimated,
        "pantry_available_quantity": sum((lot.current_quantity for lot in candidates), Decimal(0)),
        "available_lots": [
            _lot_payload(lot)
            for lot in sorted(
                candidates,
                key=lambda item: engine.lot_sort_key(
                    engine.LotCandidate(
                        item.id,
                        item.current_quantity,
                        item.normalized_unit,
                        pantry_service.date_status(item),
                        item.use_by_date or item.best_before_date,
                        item.created_at,
                    )
                ),
            )
        ],
        "allocations": allocations,
        "uncovered_quantity": max(Decimal(0), selected - allocated),
        "status_before": engine.reconciliation_status(
            required, active, reversed_quantity, decisions
        ),
        "warnings": warnings,
    }


def preview(session: Session, owner: UUID, day_id: UUID, payload: PreviewRequest) -> dict[str, Any]:
    day = consumption_service.require_day(session, owner, day_id)
    if day.version != payload.expected_day_version:
        raise error(
            "PANTRY_CONSUMPTION_PREVIEW_STALE",
            "Der Verzehrtag wurde zwischenzeitlich geändert.",
            409,
        )
    entries = _entries(day)
    if len({item.consumption_entry_id for item in payload.entries}) != len(payload.entries):
        raise error(
            "PANTRY_CONSUMPTION_DUPLICATE_DEDUCTION",
            "Ein Verzehreintrag wurde mehrfach ausgewählt.",
            409,
        )
    selected_entries: list[tuple[ConsumptionEntry, EntryDecision]] = []
    food_ids: set[UUID] = set()
    for decision in payload.entries:
        entry = entries.get(decision.consumption_entry_id)
        if entry is None:
            raise error(
                "PANTRY_CONSUMPTION_ENTRY_NOT_FOUND",
                "Ein Verzehreintrag wurde nicht gefunden.",
                404,
            )
        if entry.version != decision.expected_entry_version:
            raise error(
                "PANTRY_CONSUMPTION_ENTRY_CHANGED",
                "Ein Verzehreintrag wurde zwischenzeitlich geändert.",
                409,
            )
        selected_entries.append((entry, decision))
        if entry.food_id:
            food_ids.add(entry.food_id)
        food_ids.update(item.food_id for item in entry.recipe_ingredient_snapshots if item.food_id)
        food_ids.update(item.food_id for item in decision.requirements if item.food_id)
    lots_by_food = _lots(session, owner, food_ids)
    result_entries: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for entry, decision in selected_entries:
        requirements: list[dict[str, Any]] = []
        if decision.source_context in {
            "not_from_pantry",
            "already_accounted_for",
            "leftovers_already_accounted_for",
            "unknown",
        }:
            requirements.append(
                _requirement(
                    session,
                    entry,
                    requirement_type="direct_food"
                    if entry.entry_type == "food"
                    else "recipe_ingredient",
                    snapshot_id=None,
                    food_id=entry.food_id,
                    food_name=entry.source_display_name_snapshot,
                    required=entry.normalized_quantity,
                    unit=entry.normalized_unit,
                    estimated=entry.conversion_estimated,
                    context=decision.source_context,
                    selected=Decimal(0),
                    decision_allocations=[],
                    lots_by_food=lots_by_food,
                    normalization_status="unresolved"
                    if entry.entry_type == "manual_unresolved"
                    else "normalized",
                )
            )
            if decision.source_context == "unknown":
                warnings.append(
                    _warning(
                        "PANTRY_CONSUMPTION_SOURCE_UNKNOWN",
                        "Die Herkunft des Eintrags wurde noch nicht entschieden.",
                        affected=str(entry.id),
                    )
                )
        elif entry.entry_type == "food":
            selected = (
                decision.selected_pantry_quantity
                if decision.selected_pantry_quantity is not None
                else engine.remaining(
                    entry.normalized_quantity or Decimal(0),
                    _active_quantity(session, entry.id, None, entry.food_id)[0],
                )
            )
            requirements.append(
                _requirement(
                    session,
                    entry,
                    requirement_type="direct_food",
                    snapshot_id=None,
                    food_id=entry.food_id,
                    food_name=entry.source_display_name_snapshot,
                    required=entry.normalized_quantity,
                    unit=entry.normalized_unit,
                    estimated=entry.conversion_estimated,
                    context=decision.source_context,
                    selected=selected,
                    decision_allocations=decision.allocations,
                    lots_by_food=lots_by_food,
                )
            )
        elif entry.entry_type == "recipe":
            snapshots = list(entry.recipe_ingredient_snapshots)
            if not snapshots:
                legacy = _legacy_recipe_snapshots(entry)
                if legacy is not None and payload.confirm_legacy_recipe_snapshot:
                    snapshots = legacy
                else:
                    warnings.append(
                        _warning(
                            "PANTRY_CONSUMPTION_RECIPE_SOURCE_CHANGED"
                            if entry.recipe is not None
                            else "PANTRY_CONSUMPTION_RECIPE_SNAPSHOT_MISSING",
                            "Die historischen Zutaten dieses Rezepts können nicht zuverlässig bestimmt werden. Eine kompatible Altversion muss ausdrücklich bestätigt werden.",
                            affected=str(entry.id),
                        )
                    )
            for snapshot in snapshots:
                item_decision = _decision_for(snapshot.id, decision.requirements)
                context = (
                    item_decision.source_context
                    if item_decision
                    else ("unresolved" if not snapshot.optional_ingredient else "not_used")
                )
                selected = item_decision.selected_pantry_quantity if item_decision else Decimal(0)
                if snapshot.optional_ingredient and not (
                    item_decision and item_decision.include_optional
                ):
                    context, selected = "not_used", Decimal(0)
                    warnings.append(
                        _warning(
                            "PANTRY_CONSUMPTION_OPTIONAL_INGREDIENT_EXCLUDED",
                            "Eine optionale Zutat ist standardmäßig von der Chargenauswahl ausgeschlossen.",
                            affected=str(snapshot.id),
                        )
                    )
                requirements.append(
                    _requirement(
                        session,
                        entry,
                        requirement_type="recipe_ingredient",
                        snapshot_id=snapshot.id,
                        food_id=snapshot.food_id,
                        food_name=snapshot.food_name_snapshot,
                        required=snapshot.normalized_quantity_for_logged_portions,
                        unit=snapshot.canonical_unit,
                        estimated=snapshot.conversion_estimated,
                        context=context,
                        selected=selected,
                        decision_allocations=[]
                        if item_decision is None
                        else item_decision.allocations,
                        lots_by_food=lots_by_food,
                        optional=snapshot.optional_ingredient,
                        normalization_status=snapshot.normalization_status,
                    )
                )
            warnings.append(
                _warning(
                    "PANTRY_CONSUMPTION_RECIPE_THEORETICAL_QUANTITIES",
                    "Die Zutatenmengen werden proportional aus dem gespeicherten Rezept und der erfassten Portionsmenge berechnet. Tatsächliche Zubereitung, Reste und Verluste können davon abweichen.",
                    affected=str(entry.id),
                )
            )
        else:
            item_decision = decision.requirements[0] if decision.requirements else None
            if item_decision is None or item_decision.food_id is None:
                warnings.append(
                    _warning(
                        "PANTRY_CONSUMPTION_MANUAL_MAPPING",
                        "Der manuelle Eintrag benötigt eine ausdrückliche Lebensmittelzuordnung und Menge.",
                        affected=str(entry.id),
                    )
                )
            else:
                food = food_repository.get_food(session, owner, item_decision.food_id)
                if food is None:
                    raise error(
                        "PANTRY_CONSUMPTION_FOOD_NOT_FOUND",
                        "Das gewählte Lebensmittel wurde nicht gefunden.",
                        404,
                    )
                requirements.append(
                    _requirement(
                        session,
                        entry,
                        requirement_type="manual_mapping",
                        snapshot_id=None,
                        food_id=food.id,
                        food_name=food.name,
                        required=item_decision.selected_pantry_quantity,
                        unit=food.reference_unit,
                        estimated=False,
                        context=item_decision.source_context,
                        selected=item_decision.selected_pantry_quantity,
                        decision_allocations=item_decision.allocations,
                        lots_by_food=lots_by_food,
                        normalization_status="manual_mapping",
                    )
                )
        result_entries.append(
            {
                "consumption_entry_id": str(entry.id),
                "entry_version": entry.version,
                "entry_type": entry.entry_type,
                "display_name": entry.source_display_name_snapshot,
                "source_context": decision.source_context,
                "requirements": requirements,
            }
        )
    all_requirements = [
        requirement for item in result_entries for requirement in item["requirements"]
    ]
    all_warnings = warnings + [
        warning for requirement in all_requirements for warning in requirement["warnings"]
    ]
    body = {
        "consumption_day": {
            "id": str(day.id),
            "date": day.consumption_date.isoformat(),
            "version": day.version,
            "status": day.status,
            "completeness_attestation": day.completeness_attestation,
        },
        "apply_mode": payload.apply_mode,
        "entries": result_entries,
        "summary": {
            "entry_count": len(result_entries),
            "requirement_count": len(all_requirements),
            "allocation_count": sum(len(item["allocations"]) for item in all_requirements),
            "movement_count": sum(len(item["allocations"]) for item in all_requirements),
            "total_uncovered_requirement_count": sum(
                Decimal(str(item["uncovered_quantity"])) > 0 for item in all_requirements
            ),
            "date_warning_count": sum(
                w["code"]
                in {"PANTRY_CONSUMPTION_PAST_BEST_BEFORE_LOT", "PANTRY_CONSUMPTION_PAST_USE_BY_LOT"}
                for w in all_warnings
            ),
        },
        "warnings": all_warnings,
        "rule_version": RULE_VERSION,
        "calculated_at": datetime.now(UTC).isoformat(),
        "notice_de": "Der Vorrat wird erst nach deiner Bestätigung verändert. Verzehreinträge verändern den Vorrat nicht automatisch.",
    }
    body["preview_token"] = _token(body)
    return _json(body)


def _serialize_batch(batch: PantryConsumptionReconciliationBatch) -> dict[str, Any]:
    return _json(
        {
            "id": batch.id,
            "consumption_day_id": batch.consumption_day_id,
            "consumption_day_date": batch.consumption_day_date_snapshot,
            "status": batch.status,
            "apply_mode": batch.apply_mode,
            "source_day_version_snapshot": batch.source_day_version_snapshot,
            "source_snapshot": batch.source_snapshot,
            "rule_version": batch.rule_version,
            "applied_at": batch.applied_at,
            "reversed_at": batch.reversed_at,
            "requirements": [
                {
                    "id": r.id,
                    "consumption_entry_id": r.consumption_entry_id,
                    "requirement_type": r.requirement_type,
                    "source_context": r.source_context,
                    "food_id": r.food_id,
                    "food_name": r.food_name_snapshot,
                    "theoretical_required_quantity": r.theoretical_required_quantity,
                    "previously_reconciled_quantity": r.previously_reconciled_quantity,
                    "selected_pantry_quantity": r.selected_pantry_quantity,
                    "canonical_unit": r.canonical_unit,
                    "status": r.status,
                    "allocations": [
                        {
                            "id": a.id,
                            "stock_lot_id": a.pantry_stock_lot_id,
                            "pantry_movement_id": a.pantry_movement_id,
                            "location_name": a.location_name_snapshot,
                            "allocated_quantity": a.allocated_quantity,
                            "canonical_unit": a.canonical_unit,
                            "lot_available_before": a.lot_available_before,
                            "lot_available_after": a.lot_available_after,
                            "date_status": a.lot_date_status_snapshot,
                            "reversed_quantity": sum(
                                (x.reversal_quantity for x in a.reversal_allocations), Decimal(0)
                            ),
                        }
                        for a in r.allocations
                    ],
                }
                for r in batch.requirements
            ],
        }
    )


def apply(session: Session, owner: UUID, day_id: UUID, payload: ApplyRequest) -> dict[str, Any]:
    duplicate = session.scalar(
        select(PantryConsumptionReconciliationBatch)
        .where(
            PantryConsumptionReconciliationBatch.owner_profile_id == owner,
            PantryConsumptionReconciliationBatch.client_operation_id == payload.client_operation_id,
        )
        .options(
            selectinload(PantryConsumptionReconciliationBatch.requirements)
            .selectinload(PantryConsumptionRequirement.allocations)
            .selectinload(PantryConsumptionAllocation.reversal_allocations)
        )
    )
    if duplicate:
        return _serialize_batch(duplicate)
    current = preview(session, owner, day_id, payload.preview)
    if current["preview_token"] != payload.preview_token:
        raise error(
            "PANTRY_CONSUMPTION_PREVIEW_STALE",
            "Vorrat oder Verzehrdaten haben sich geändert. Bitte Vorschau neu erstellen.",
            409,
        )
    past_use_by = {
        allocation["stock_lot_id"]
        for entry in current["entries"]
        for requirement in entry["requirements"]
        for allocation in requirement["allocations"]
        if allocation["date_status"] == "past_use_by"
    }
    if not past_use_by <= {str(item) for item in payload.past_use_by_confirmations}:
        raise error(
            "PANTRY_CONSUMPTION_DATE_CONFIRMATION_REQUIRED",
            "Eine Charge mit überschrittenem Verbrauchsdatum muss ausdrücklich bestätigt werden.",
            409,
        )
    day = consumption_service.require_day(session, owner, day_id, lock=True)
    if payload.preview.confirm_legacy_recipe_snapshot:
        for entry in _entries(day).values():
            if entry.entry_type == "recipe" and not entry.recipe_ingredient_snapshots:
                snapshots = _legacy_recipe_snapshots(entry)
                if snapshots is not None:
                    session.add_all(snapshots)
        session.flush()
    batch = PantryConsumptionReconciliationBatch(
        owner_profile_id=owner,
        consumption_day_id=day.id,
        consumption_day_date_snapshot=day.consumption_date,
        apply_mode=payload.preview.apply_mode,
        client_operation_id=payload.client_operation_id,
        source_day_version_snapshot=day.version,
        source_snapshot={
            "date": day.consumption_date.isoformat(),
            "entries": [
                {
                    "id": item["consumption_entry_id"],
                    "display_name": item["display_name"],
                    "entry_type": item["entry_type"],
                }
                for item in current["entries"]
            ],
        },
    )
    session.add(batch)
    session.flush()
    for entry_data in current["entries"]:
        for requirement_data in entry_data["requirements"]:
            selected = Decimal(str(requirement_data["selected_pantry_quantity"]))
            uncovered = Decimal(str(requirement_data["uncovered_quantity"]))
            if payload.preview.apply_mode == "all_or_nothing" and uncovered > 0:
                raise error(
                    "PANTRY_CONSUMPTION_INSUFFICIENT_STOCK",
                    "Im Modus Alles-oder-nichts müssen alle gewählten Mengen vollständig gedeckt sein.",
                    409,
                )
            status = (
                "decision_only"
                if selected == 0
                else "partially_reconciled"
                if uncovered > 0
                else "reconciled"
            )
            requirement = PantryConsumptionRequirement(
                batch_id=batch.id,
                owner_profile_id=owner,
                consumption_day_id=day.id,
                consumption_entry_id=UUID(entry_data["consumption_entry_id"]),
                consumption_entry_version_snapshot=int(entry_data["entry_version"]),
                requirement_type=requirement_data["requirement_type"],
                source_context=requirement_data["source_context"],
                food_id=None
                if requirement_data["food_id"] is None
                else UUID(requirement_data["food_id"]),
                food_name_snapshot=requirement_data["food_name"],
                recipe_ingredient_snapshot_id=None
                if requirement_data["recipe_ingredient_snapshot_id"] is None
                else UUID(requirement_data["recipe_ingredient_snapshot_id"]),
                theoretical_required_quantity=None
                if requirement_data["theoretical_required_quantity"] is None
                else Decimal(str(requirement_data["theoretical_required_quantity"])),
                previously_reconciled_quantity=Decimal(
                    str(requirement_data["previously_reconciled_quantity"])
                ),
                selected_pantry_quantity=selected,
                canonical_unit=requirement_data["canonical_unit"],
                normalization_status=requirement_data["normalization_status"],
                conversion_estimated=bool(requirement_data["conversion_estimated"]),
                status=status,
                calculation_metadata={
                    "rule_version": RULE_VERSION,
                    "remaining_before": requirement_data["remaining_reconcilable_quantity"],
                    "uncovered": requirement_data["uncovered_quantity"],
                    "entry_snapshot": {
                        "display_name": entry_data["display_name"],
                        "entry_type": entry_data["entry_type"],
                    },
                },
            )
            session.add(requirement)
            session.flush()
            for allocation_data in requirement_data["allocations"]:
                quantity = Decimal(str(allocation_data["allocated_quantity"]))
                operation_id = uuid5(
                    batch.id, f"{requirement.id}:{allocation_data['stock_lot_id']}"
                )
                pantry_service.operate(
                    session,
                    owner,
                    UUID(allocation_data["stock_lot_id"]),
                    QuantityOperation(
                        client_operation_id=operation_id,
                        quantity=quantity,
                        unit_code=requirement.canonical_unit or "g",
                    ),
                    "consume",
                    commit=False,
                    source_type="consumption_reconciliation",
                )
                movement = session.scalar(
                    select(PantryMovement).where(
                        PantryMovement.owner_profile_id == owner,
                        PantryMovement.client_operation_id == operation_id,
                    )
                )
                assert movement is not None
                lot = pantry_service._lot(session, owner, UUID(allocation_data["stock_lot_id"]))
                requirement.allocations.append(
                    PantryConsumptionAllocation(
                        pantry_stock_lot_id=lot.id,
                        pantry_movement_id=movement.id,
                        food_id=requirement.food_id,
                        location_id_snapshot=lot.location_id,
                        location_name_snapshot=allocation_data["location_name"],
                        allocated_quantity=quantity,
                        canonical_unit=requirement.canonical_unit or lot.normalized_unit,
                        lot_available_before=movement.balance_before,
                        lot_available_after=movement.balance_after,
                        lot_date_status_snapshot=allocation_data["date_status"],
                        relevant_date_snapshot=None
                        if allocation_data["relevant_date"] is None
                        else date.fromisoformat(allocation_data["relevant_date"]),
                        conversion_estimated=requirement.conversion_estimated,
                    )
                )
    session.commit()
    return detail(session, owner, batch.id)


def deletion_preview(
    session: Session, owner: UUID, *, day_id: UUID, entry_id: UUID | None = None
) -> dict[str, Any]:
    day = consumption_service.require_day(session, owner, day_id)
    query = (
        select(PantryConsumptionReconciliationBatch)
        .join(PantryConsumptionRequirement)
        .where(
            PantryConsumptionReconciliationBatch.owner_profile_id == owner,
            PantryConsumptionReconciliationBatch.status.in_(("active", "partially_reversed")),
            PantryConsumptionRequirement.consumption_day_id == day.id,
        )
    )
    if entry_id is not None:
        if entry_id not in _entries(day):
            raise error(
                "PANTRY_CONSUMPTION_ENTRY_NOT_FOUND",
                "Der Verzehreintrag wurde nicht gefunden.",
                404,
            )
        query = query.where(PantryConsumptionRequirement.consumption_entry_id == entry_id)
    batches = list(
        session.scalars(
            query.options(
                selectinload(PantryConsumptionReconciliationBatch.requirements)
                .selectinload(PantryConsumptionRequirement.allocations)
                .selectinload(PantryConsumptionAllocation.reversal_allocations)
            )
        ).unique()
    )
    affected: list[dict[str, Any]] = []
    for batch in batches:
        for requirement in batch.requirements:
            if entry_id is not None and requirement.consumption_entry_id != entry_id:
                continue
            for allocation in requirement.allocations:
                reversed_quantity = sum(
                    (item.reversal_quantity for item in allocation.reversal_allocations), Decimal(0)
                )
                active = allocation.allocated_quantity - reversed_quantity
                if active > 0:
                    affected.append(
                        {
                            "batch_id": str(batch.id),
                            "allocation_id": str(allocation.id),
                            "food_name": requirement.food_name_snapshot,
                            "active_quantity": active,
                            "canonical_unit": allocation.canonical_unit,
                            "location_name": allocation.location_name_snapshot,
                        }
                    )
    return {
        "consumption_day_id": str(day.id),
        "consumption_entry_id": None if entry_id is None else str(entry_id),
        "requires_resolution": bool(affected),
        "active_allocations": affected,
        "options": ["reverse_and_delete", "keep_pantry_movements_and_delete", "cancel"]
        if entry_id
        else ["reverse_all_and_delete", "keep_all_movements_and_delete", "cancel"],
    }


def _reverse_for_deletion(
    session: Session,
    owner: UUID,
    allocations_by_batch: dict[UUID, list[dict[str, Any]]],
    operation_id: UUID,
) -> None:
    for batch_id, selections in allocations_by_batch.items():
        request = ReversalPreviewRequest(
            reason="consumption_entry_deleted",
            note=None,
            selections=[ReversalSelection.model_validate(item) for item in selections],
        )
        current = reversal_preview(session, owner, batch_id, request)
        reverse(
            session,
            owner,
            batch_id,
            ReversalApplyRequest(
                client_operation_id=uuid5(operation_id, str(batch_id)),
                preview_token=current["preview_token"],
                preview=request,
            ),
        )


def delete_entry_with_resolution(
    session: Session, owner: UUID, day_id: UUID, entry_id: UUID, payload: EntryDeletionResolution
) -> dict[str, bool]:
    if payload.policy == "cancel":
        return {"deleted": False}
    preview_data = deletion_preview(session, owner, day_id=day_id, entry_id=entry_id)
    if preview_data["requires_resolution"] and payload.policy == "reverse_and_delete":
        assert payload.client_operation_id is not None
        grouped: dict[UUID, list[dict[str, Any]]] = {}
        for item in preview_data["active_allocations"]:
            grouped.setdefault(UUID(item["batch_id"]), []).append(
                {"allocation_id": UUID(item["allocation_id"]), "quantity": item["active_quantity"]}
            )
        _reverse_for_deletion(session, owner, grouped, payload.client_operation_id)
    day = consumption_service.require_day(session, owner, day_id, lock=True)
    entry = _entries(day).get(entry_id)
    if entry is None:
        raise error(
            "PANTRY_CONSUMPTION_ENTRY_NOT_FOUND", "Der Verzehreintrag wurde nicht gefunden.", 404
        )
    session.delete(entry)
    day.version += 1
    session.commit()
    return {"deleted": True}


def delete_day_with_resolution(
    session: Session, owner: UUID, day_id: UUID, payload: DayDeletionResolution
) -> dict[str, bool]:
    if payload.policy == "cancel":
        return {"deleted": False}
    preview_data = deletion_preview(session, owner, day_id=day_id)
    if preview_data["requires_resolution"] and payload.policy == "reverse_all_and_delete":
        if payload.client_operation_id is None:
            raise error(
                "PANTRY_CONSUMPTION_DELETION_RESOLUTION_REQUIRED",
                "Für die Gegenbewegungen ist eine Vorgangs-ID erforderlich.",
            )
        grouped: dict[UUID, list[dict[str, Any]]] = {}
        for item in preview_data["active_allocations"]:
            grouped.setdefault(UUID(item["batch_id"]), []).append(
                {"allocation_id": UUID(item["allocation_id"]), "quantity": item["active_quantity"]}
            )
        _reverse_for_deletion(session, owner, grouped, payload.client_operation_id)
    day = consumption_service.require_day(session, owner, day_id, lock=True)
    session.delete(day)
    session.commit()
    return {"deleted": True}


def _batch(session: Session, owner: UUID, batch_id: UUID) -> PantryConsumptionReconciliationBatch:
    item = session.scalar(
        select(PantryConsumptionReconciliationBatch)
        .where(
            PantryConsumptionReconciliationBatch.id == batch_id,
            PantryConsumptionReconciliationBatch.owner_profile_id == owner,
        )
        .options(
            selectinload(PantryConsumptionReconciliationBatch.requirements)
            .selectinload(PantryConsumptionRequirement.allocations)
            .selectinload(PantryConsumptionAllocation.reversal_allocations),
            selectinload(PantryConsumptionReconciliationBatch.reversals),
        )
    )
    if item is None:
        raise error(
            "PANTRY_CONSUMPTION_BATCH_NOT_FOUND", "Der Bestandsabgleich wurde nicht gefunden.", 404
        )
    return item


def detail(session: Session, owner: UUID, batch_id: UUID) -> dict[str, Any]:
    return _serialize_batch(_batch(session, owner, batch_id))


def history(
    session: Session,
    owner: UUID,
    *,
    day_id: UUID | None = None,
    entry_id: UUID | None = None,
    food_id: UUID | None = None,
    lot_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    has_reversal: bool | None = None,
    sort: str = "applied_at_desc",
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    query = select(PantryConsumptionReconciliationBatch).where(
        PantryConsumptionReconciliationBatch.owner_profile_id == owner
    )
    if day_id:
        query = query.where(PantryConsumptionReconciliationBatch.consumption_day_id == day_id)
    if status:
        query = query.where(PantryConsumptionReconciliationBatch.status == status)
    if entry_id or food_id or lot_id:
        query = query.join(PantryConsumptionRequirement).where(
            *([PantryConsumptionRequirement.consumption_entry_id == entry_id] if entry_id else []),
            *([PantryConsumptionRequirement.food_id == food_id] if food_id else []),
        )
    if lot_id:
        query = query.join(PantryConsumptionAllocation).where(
            PantryConsumptionAllocation.pantry_stock_lot_id == lot_id
        )
    if date_from:
        query = query.where(
            PantryConsumptionReconciliationBatch.consumption_day_date_snapshot >= date_from
        )
    if date_to:
        query = query.where(
            PantryConsumptionReconciliationBatch.consumption_day_date_snapshot <= date_to
        )
    if has_reversal is not None:
        query = query.where(
            PantryConsumptionReconciliationBatch.status != "active"
            if has_reversal
            else PantryConsumptionReconciliationBatch.status == "active"
        )
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        session.scalars(
            query.options(
                selectinload(PantryConsumptionReconciliationBatch.requirements)
                .selectinload(PantryConsumptionRequirement.allocations)
                .selectinload(PantryConsumptionAllocation.reversal_allocations)
            )
            .order_by(
                PantryConsumptionReconciliationBatch.applied_at.asc()
                if sort == "applied_at_asc"
                else PantryConsumptionReconciliationBatch.applied_at.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique()
    )
    return {
        "items": [_serialize_batch(item) for item in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def status_for_day(session: Session, owner: UUID, day_id: UUID) -> dict[str, Any]:
    day = consumption_service.require_day(session, owner, day_id)
    summaries = [status_for_entry(session, owner, entry.id) for entry in _entries(day).values()]
    return {
        "consumption_day_id": str(day.id),
        "entries": summaries,
        "summary": {
            "entry_count": len(summaries),
            "not_started_count": sum(x["status"] == "not_started" for x in summaries),
            "partial_count": sum(
                x["status"] in {"partially_reconciled", "partially_reversed"} for x in summaries
            ),
            "complete_count": sum(x["status"] == "fully_reconciled" for x in summaries),
            "not_from_pantry_count": sum(x["status"] == "not_from_pantry" for x in summaries),
            "already_accounted_count": sum(
                x["status"] == "already_accounted_for" for x in summaries
            ),
            "unresolved_count": sum(x["status"] == "unresolved" for x in summaries),
        },
    }


def status_for_entry(session: Session, owner: UUID, entry_id: UUID) -> dict[str, Any]:
    entry = session.scalar(
        select(ConsumptionEntry)
        .where(ConsumptionEntry.id == entry_id, ConsumptionEntry.owner_profile_id == owner)
        .options(selectinload(ConsumptionEntry.recipe_ingredient_snapshots))
    )
    if entry is None:
        raise error(
            "PANTRY_CONSUMPTION_ENTRY_NOT_FOUND", "Der Verzehreintrag wurde nicht gefunden.", 404
        )
    if entry.entry_type == "recipe":
        requirement_statuses: list[dict[str, Any]] = []
        for snapshot in entry.recipe_ingredient_snapshots:
            active, reversed_quantity, decisions = _active_quantity(
                session, entry.id, snapshot.id, snapshot.food_id
            )
            required = snapshot.normalized_quantity_for_logged_portions
            requirement_statuses.append(
                {
                    "recipe_ingredient_snapshot_id": snapshot.id,
                    "food_id": snapshot.food_id,
                    "food_name": snapshot.food_name_snapshot,
                    "required_quantity": required,
                    "canonical_unit": snapshot.canonical_unit,
                    "active_reconciled_quantity": active,
                    "remaining_quantity": engine.remaining(required, active),
                    "reversed_quantity": reversed_quantity,
                    "status": engine.reconciliation_status(
                        required, active, reversed_quantity, decisions
                    ),
                    "optional_ingredient": snapshot.optional_ingredient,
                }
            )
        relevant = [item for item in requirement_statuses if not item["optional_ingredient"]]
        statuses = {item["status"] for item in relevant}
        if not relevant or statuses <= {"not_started"}:
            status = "not_started"
        elif statuses <= {"fully_reconciled", "not_from_pantry", "already_accounted_for"}:
            status = "fully_reconciled"
        elif "unresolved" in statuses:
            status = "unresolved"
        elif any(item["active_reconciled_quantity"] > 0 for item in relevant):
            status = "partially_reconciled"
        else:
            status = "not_started"
        return _json(
            {
                "consumption_entry_id": entry.id,
                "entry_type": entry.entry_type,
                "display_name": entry.source_display_name_snapshot,
                "required_quantity": None,
                "active_reconciled_quantity": None,
                "remaining_quantity": None,
                "reversed_quantity": sum(
                    (item["reversed_quantity"] for item in requirement_statuses), Decimal(0)
                ),
                "status": status,
                "requirements": requirement_statuses,
            }
        )
    active, reversed_quantity, decisions = _active_quantity(session, entry.id, None, entry.food_id)
    required = entry.normalized_quantity
    status = engine.reconciliation_status(required, active, reversed_quantity, decisions)
    return _json(
        {
            "consumption_entry_id": entry.id,
            "entry_type": entry.entry_type,
            "display_name": entry.source_display_name_snapshot,
            "required_quantity": required,
            "active_reconciled_quantity": active,
            "remaining_quantity": None if required is None else engine.remaining(required, active),
            "reversed_quantity": reversed_quantity,
            "status": status,
        }
    )


def reversal_preview(
    session: Session, owner: UUID, batch_id: UUID, payload: ReversalPreviewRequest
) -> dict[str, Any]:
    batch = _batch(session, owner, batch_id)
    allocations = {a.id: a for r in batch.requirements for a in r.allocations}
    results = []
    for selection in payload.selections:
        allocation = allocations.get(selection.allocation_id)
        if allocation is None:
            raise error(
                "PANTRY_CONSUMPTION_ALLOCATION_NOT_FOUND",
                "Eine Bestandsbewegung wurde nicht gefunden.",
                404,
            )
        already = sum(
            (item.reversal_quantity for item in allocation.reversal_allocations), Decimal(0)
        )
        if selection.quantity > allocation.allocated_quantity - already:
            raise error(
                "PANTRY_CONSUMPTION_REVERSAL_EXCEEDS_ALLOCATION",
                "Die Gegenbewegung übersteigt die aktive ursprüngliche Menge.",
                409,
            )
        target_id = selection.target_lot_id or allocation.pantry_stock_lot_id
        if target_id is None:
            raise error(
                "PANTRY_CONSUMPTION_REVERSAL_TARGET_REQUIRED",
                "Für die Gegenbewegung muss eine Charge gewählt werden.",
                409,
            )
        lot = pantry_service._lot(session, owner, target_id)
        if lot.is_archived or lot.location.is_archived:
            raise error(
                "PANTRY_CONSUMPTION_REVERSAL_TARGET_REQUIRED",
                "Eine archivierte Charge muss zuerst ausdrücklich wiederhergestellt werden.",
                409,
            )
        if lot.food_id != allocation.food_id or lot.normalized_unit != allocation.canonical_unit:
            raise error(
                "PANTRY_CONSUMPTION_FOOD_MISMATCH",
                "Die Zielcharge passt nicht zur ursprünglichen Bewegung.",
                409,
            )
        results.append(
            {
                "allocation_id": str(allocation.id),
                "original_movement_id": str(allocation.pantry_movement_id),
                "target_lot_id": str(lot.id),
                "original_quantity": allocation.allocated_quantity,
                "already_reversed_quantity": already,
                "selected_reversal_quantity": selection.quantity,
                "lot_quantity_before": lot.current_quantity,
                "lot_quantity_after": lot.current_quantity + selection.quantity,
                "lot_version": lot.version,
            }
        )
    body = {
        "batch_id": str(batch.id),
        "reason": payload.reason,
        "note": payload.note,
        "allocations": results,
        "explanation_de": "Die ursprünglichen Bestandsbewegungen bleiben erhalten. Für die Korrektur werden Gegenbewegungen erstellt.",
        "calculated_at": datetime.now(UTC).isoformat(),
    }
    body["preview_token"] = _token(body)
    return _json(body)


def reverse(
    session: Session, owner: UUID, batch_id: UUID, payload: ReversalApplyRequest
) -> dict[str, Any]:
    duplicate = session.scalar(
        select(PantryConsumptionReversal).where(
            PantryConsumptionReversal.owner_profile_id == owner,
            PantryConsumptionReversal.client_operation_id == payload.client_operation_id,
        )
    )
    if duplicate:
        return detail(session, owner, duplicate.reconciliation_batch_id)
    current = reversal_preview(session, owner, batch_id, payload.preview)
    if current["preview_token"] != payload.preview_token:
        raise error(
            "PANTRY_CONSUMPTION_PREVIEW_STALE",
            "Die Bestände haben sich geändert. Bitte Gegenbewegung erneut prüfen.",
            409,
        )
    batch = _batch(session, owner, batch_id)
    allocations = {a.id: a for r in batch.requirements for a in r.allocations}
    reversal = PantryConsumptionReversal(
        owner_profile_id=owner,
        reconciliation_batch_id=batch.id,
        client_operation_id=payload.client_operation_id,
        reason=payload.preview.reason,
        note=payload.preview.note,
        status="applied",
    )
    session.add(reversal)
    session.flush()
    for index, item in enumerate(current["allocations"]):
        allocation = allocations[UUID(item["allocation_id"])]
        quantity = Decimal(str(item["selected_reversal_quantity"]))
        operation_id = uuid5(reversal.id, str(index))
        pantry_service.operate(
            session,
            owner,
            UUID(item["target_lot_id"]),
            QuantityOperation(
                client_operation_id=operation_id,
                quantity=quantity,
                unit_code=allocation.canonical_unit,
                confirm_depleted_reuse=True,
            ),
            "add_stock",
            commit=False,
            source_type="consumption_reconciliation_reversal",
        )
        movement = session.scalar(
            select(PantryMovement).where(
                PantryMovement.owner_profile_id == owner,
                PantryMovement.client_operation_id == operation_id,
            )
        )
        assert movement is not None
        reversal.allocations.append(
            PantryConsumptionReversalAllocation(
                original_allocation_id=allocation.id,
                reversal_quantity=quantity,
                compensating_pantry_movement_id=movement.id,
                lot_quantity_before=movement.balance_before,
                lot_quantity_after=movement.balance_after,
            )
        )
    session.flush()
    active = sum(
        (a.allocated_quantity for r in batch.requirements for a in r.allocations), Decimal(0)
    ) - sum(
        (
            x.reversal_quantity
            for r in batch.requirements
            for a in r.allocations
            for x in a.reversal_allocations
        ),
        Decimal(0),
    )
    batch.status = "fully_reversed" if active == 0 else "partially_reversed"
    batch.reversed_at = datetime.now(UTC) if active == 0 else None
    session.commit()
    return detail(session, owner, batch.id)
