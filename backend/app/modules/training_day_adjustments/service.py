# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-any-return,arg-type,assignment,index,operator,call-overload"
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.modules.daily_meal_planning import repository as plan_repository
from app.modules.daily_meal_planning.models import DailyMealPlan
from app.modules.nutrition_assessment import repository as assessment_repository
from app.modules.nutrition_assessment.models import Assessment
from app.modules.recipe_target_comparison.target_extraction import extract_targets, is_usable

from . import engine, rules
from .models import (
    TrainingAdjustmentBatch,
    TrainingAdjustmentPreference,
    TrainingDayTargetAdjustment,
    TrainingSession,
)
from .schemas import ApplyRequest, PreferenceWrite, PreviewRequest, SessionWrite


def error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code, message, status)


def encode(value: object) -> Any:
    return jsonable_encoder(value, custom_encoder={Decimal: str})


def row(item: Any) -> dict[str, Any]:
    return encode({column.name: getattr(item, column.name) for column in item.__table__.columns})


def require_session(db: Session, owner: UUID, item_id: UUID) -> TrainingSession:
    item = db.scalar(
        select(TrainingSession).where(
            TrainingSession.id == item_id, TrainingSession.owner_profile_id == owner
        )
    )
    if item is None:
        raise error("TRAINING_SESSION_NOT_FOUND", "Die Trainingseinheit wurde nicht gefunden.", 404)
    return item


def list_sessions(
    db: Session, owner: UUID, start: date | None, end: date | None, include_cancelled: bool
) -> list[dict]:
    query = select(TrainingSession).where(TrainingSession.owner_profile_id == owner)
    if start:
        query = query.where(TrainingSession.session_date >= start)
    if end:
        query = query.where(TrainingSession.session_date <= end)
    if not include_cancelled:
        query = query.where(TrainingSession.status != "cancelled")
    return [
        row(item)
        for item in db.scalars(
            query.order_by(TrainingSession.session_date, TrainingSession.planned_start_time)
        ).all()
    ]


def save_session(
    db: Session, owner: UUID, payload: SessionWrite, item_id: UUID | None = None
) -> dict:
    if payload.planned_duration_minutes > 480 and not payload.confirm_long_duration:
        raise error(
            "TRAINING_SESSION_LONG_DURATION_CONFIRMATION_REQUIRED",
            "Bitte bestätige die ungewöhnlich lange geplante Dauer.",
            409,
        )
    item = (
        require_session(db, owner, item_id) if item_id else TrainingSession(owner_profile_id=owner)
    )
    if (
        payload.expected_version is not None
        and item_id
        and item.version != payload.expected_version
    ):
        raise error(
            "TRAINING_ADJUSTMENT_CONCURRENT_MODIFICATION",
            "Die Trainingseinheit wurde zwischenzeitlich geändert.",
            409,
        )
    values = payload.model_dump(exclude={"expected_version", "confirm_long_duration"})
    for key, value in values.items():
        setattr(item, key, value.value if hasattr(value, "value") else value)
    if item_id:
        item.version += 1
    else:
        db.add(item)
    db.commit()
    db.refresh(item)
    return row(item)


def set_session_status(db: Session, owner: UUID, item_id: UUID, status: str) -> dict:
    item = require_session(db, owner, item_id)
    now = datetime.now(UTC)
    item.status = status
    item.version += 1
    item.completed_at = now if status == "completed" else None
    item.cancelled_at = now if status == "cancelled" else None
    db.commit()
    db.refresh(item)
    result = row(item)
    result["adjustment_stale_notice_de"] = (
        "Bereits gespeicherte Tagesanpassungen bleiben unverändert. Du kannst sie ausdrücklich neu berechnen."
    )
    return result


def delete_session(db: Session, owner: UUID, item_id: UUID) -> dict:
    item = require_session(db, owner, item_id)
    referenced = any(
        str(item_id) in list(snapshot.calculation_metadata.get("session_ids", []))
        for snapshot in db.scalars(
            select(TrainingDayTargetAdjustment).where(
                TrainingDayTargetAdjustment.owner_profile_id == owner
            )
        )
    )
    if referenced:
        raise error(
            "TRAINING_SESSION_REFERENCED_BY_ADJUSTMENT",
            "Die Einheit ist Teil einer unveränderlichen Anpassung und kann nur abgesagt werden.",
            409,
        )
    db.delete(item)
    db.commit()
    return {"deleted": True, "id": str(item_id)}


def _preference(db: Session, owner: UUID, item_id: UUID | None) -> TrainingAdjustmentPreference:
    item = (
        db.scalar(
            select(TrainingAdjustmentPreference).where(
                TrainingAdjustmentPreference.owner_profile_id == owner,
                TrainingAdjustmentPreference.id == item_id,
            )
        )
        if item_id
        else db.scalar(
            select(TrainingAdjustmentPreference).where(
                TrainingAdjustmentPreference.owner_profile_id == owner,
                TrainingAdjustmentPreference.is_default.is_(True),
                TrainingAdjustmentPreference.is_archived.is_(False),
            )
        )
    )
    if item is None and item_id:
        raise error(
            "TRAINING_ADJUSTMENT_PREFERENCE_NOT_FOUND",
            "Die Anpassungseinstellung wurde nicht gefunden.",
            404,
        )
    if item is None:
        item = TrainingAdjustmentPreference(
            owner_profile_id=owner, name="Konservative Standardwerte", is_default=True
        )
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


def list_preferences(db: Session, owner: UUID, include_archived: bool = False) -> list[dict]:
    _preference(db, owner, None)
    query = select(TrainingAdjustmentPreference).where(
        TrainingAdjustmentPreference.owner_profile_id == owner
    )
    if not include_archived:
        query = query.where(TrainingAdjustmentPreference.is_archived.is_(False))
    return [
        row(item)
        for item in db.scalars(
            query.order_by(
                TrainingAdjustmentPreference.is_default.desc(),
                TrainingAdjustmentPreference.created_at,
            )
        ).all()
    ]


def save_preference(
    db: Session, owner: UUID, payload: PreferenceWrite, item_id: UUID | None = None
) -> dict:
    item = (
        _preference(db, owner, item_id)
        if item_id
        else TrainingAdjustmentPreference(owner_profile_id=owner)
    )
    if (
        payload.explicit_assessment_id
        and assessment_repository.get_assessment(db, owner, payload.explicit_assessment_id) is None
    ):
        raise error(
            "TRAINING_ADJUSTMENT_ASSESSMENT_NOT_FOUND", "Das Assessment wurde nicht gefunden.", 404
        )
    if payload.is_default:
        for old in db.scalars(
            select(TrainingAdjustmentPreference).where(
                TrainingAdjustmentPreference.owner_profile_id == owner,
                TrainingAdjustmentPreference.is_default.is_(True),
            )
        ):
            old.is_default = False
    for key, value in payload.model_dump().items():
        setattr(item, key, value.value if hasattr(value, "value") else value)
    if not item_id:
        db.add(item)
    db.commit()
    db.refresh(item)
    return row(item)


def archive_preference(db: Session, owner: UUID, item_id: UUID, restore: bool = False) -> dict:
    item = _preference(db, owner, item_id)
    item.is_archived = not restore
    item.archived_at = None if restore else datetime.now(UTC)
    if item.is_archived:
        item.is_default = False
    db.commit()
    db.refresh(item)
    return row(item)


def _assessment(db: Session, owner: UUID, requested: UUID | None) -> Assessment:
    item = (
        assessment_repository.get_assessment(db, owner, requested)
        if requested
        else next(
            (
                value
                for value in assessment_repository.list_assessments_with_metrics(db, owner)
                if is_usable(value)
            ),
            None,
        )
    )
    if item is None:
        raise error(
            "TRAINING_ADJUSTMENT_ASSESSMENT_NOT_FOUND",
            "Es liegt kein nutzbares Assessment vor.",
            404,
        )
    energy = item.summary.get("energy_target", {})
    if not is_usable(item) or not isinstance(energy, dict) or not energy.get("available"):
        raise error(
            "TRAINING_ADJUSTMENT_ASSESSMENT_UNSUPPORTED",
            "Das Assessment enthält kein nutzbares Energieziel.",
            409,
        )
    return item


def _range(payload: PreviewRequest) -> tuple[date, date]:
    if payload.scope == "single_day":
        assert payload.date
        return payload.date, payload.date
    assert payload.week_anchor_date
    start = payload.week_anchor_date - timedelta(days=payload.week_anchor_date.weekday())
    return start, start + timedelta(days=6)


def _targets(
    assessment: Assessment,
) -> tuple[Decimal, Decimal, dict[str, object], dict[str, object]]:
    energy = assessment.summary["energy_target"]
    assert isinstance(energy, dict)
    baseline = Decimal(str(energy["midpoint"]))
    floor = Decimal(str(energy["lower"]))
    targets = {item.nutrient_code: item for item in extract_targets(assessment)}
    carb = targets.get("carbohydrate")
    protein = targets.get("protein")

    def snap(value: Any) -> dict[str, object]:
        if value is None:
            return {"available": False}
        return {
            "available": True,
            "target_kind": value.target_kind,
            "value": str(value.value),
            "minimum": None if value.minimum is None else str(value.minimum),
            "maximum": None if value.maximum is None else str(value.maximum),
            "unit": value.unit,
        }

    return baseline, floor, snap(carb), snap(protein)


def _session_input(item: TrainingSession) -> engine.SessionInput:
    return engine.SessionInput(
        str(item.id),
        item.session_date,
        item.planned_duration_minutes,
        item.perceived_intensity,
        item.session_type,
        item.baseline_inclusion,
        item.version,
    )


def preview(db: Session, owner: UUID, payload: PreviewRequest) -> dict[str, Any]:
    start, end = _range(payload)
    assessment = _assessment(db, owner, payload.source_assessment_id)
    pref = _preference(db, owner, payload.preference_id)
    query = select(TrainingSession).where(
        TrainingSession.owner_profile_id == owner,
        TrainingSession.session_date >= start,
        TrainingSession.session_date <= end,
    )
    if not pref.include_cancelled_sessions:
        query = query.where(TrainingSession.status != "cancelled")
    sessions = list(db.scalars(query.order_by(TrainingSession.session_date, TrainingSession.id)))
    if payload.session_ids is not None:
        selected = set(payload.session_ids)
        if not selected <= {item.id for item in sessions}:
            raise error(
                "TRAINING_SESSION_NOT_FOUND",
                "Mindestens eine ausgewählte Einheit wurde nicht gefunden.",
                404,
            )
        sessions = [item for item in sessions if item.id in selected]
    baseline, floor, carb, protein = _targets(assessment)
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    by_date = {day: [item for item in sessions if item.session_date == day] for day in dates}
    classified = {
        day: engine.classify([_session_input(item) for item in values])
        for day, values in by_date.items()
    }
    if payload.strategy.value == "weekly_redistribution" and payload.scope != "iso_week":
        raise error(
            "TRAINING_ADJUSTMENT_INVALID_STRATEGY",
            "Die wöchentliche Umverteilung benötigt eine vollständige ISO-Woche.",
        )
    redistributed: dict[date, dict[str, object]] = {}
    if payload.strategy.value == "weekly_redistribution":
        if not pref.redistribution_enabled:
            raise error(
                "TRAINING_ADJUSTMENT_INVALID_STRATEGY",
                "Die Umverteilung ist in dieser Einstellung deaktiviert.",
            )
        try:
            values = engine.redistribute(
                [(day, str(classified[day]["category"])) for day in dates],
                baseline,
                pref.positive_energy_cap_kcal,
                pref.negative_energy_cap_kcal,
                pref.relative_energy_cap,
                max(floor, pref.minimum_rest_day_target_kcal or Decimal(0)),
                payload.redistribution_strength,
            )
        except ValueError:
            raise error(
                "TRAINING_ADJUSTMENT_REDISTRIBUTION_INFEASIBLE",
                "Die Wochenenergie kann innerhalb der gewählten Grenzen nicht sicher verteilt werden.",
                409,
            ) from None
        redistributed = {date.fromisoformat(str(value["date"])): value for value in values}
    warnings: list[dict[str, object]] = [
        {
            "code": "TRAINING_ADJUSTMENT_RULE_HEURISTIC",
            "severity": "info",
            "explanation_de": "Die Belastungskategorien und Bereiche sind versionierte Planungshilfen, keine Messung des Trainingsverbrauchs.",
            "suggested_action_de": "Prüfe die Annahmen und wähle die Anpassung bewusst.",
        }
    ]
    day_results = []
    for day in dates:
        items = by_date[day]
        classification = classified[day]
        category = str(classification["category"])
        selected_energy = payload.selected_energy_deltas.get(day.isoformat())
        if payload.strategy.value == "weekly_redistribution":
            delta = Decimal(str(redistributed[day]["delta"]))
            suggested_min = suggested_max = delta
            cap = pref.positive_energy_cap_kcal
        elif payload.strategy.value == "bounded_additive":
            try:
                add = engine.additive(
                    category,
                    baseline,
                    [_session_input(item) for item in items],
                    pref.positive_energy_cap_kcal,
                    pref.relative_energy_cap,
                    selected_energy,
                )
            except ValueError:
                raise error(
                    "TRAINING_ADJUSTMENT_CAP_EXCEEDED",
                    "Die gewählte Anpassung liegt außerhalb der zulässigen Grenzen.",
                ) from None
            delta = Decimal(str(add["selected"]))
            suggested_min = Decimal(str(add["suggested_min"]))
            suggested_max = Decimal(str(add["suggested_max"]))
            cap = Decimal(str(add["cap"]))
            if not add["allowed"] and delta == 0:
                warnings.append(
                    {
                        "code": "TRAINING_ADJUSTMENT_BASELINE_INCLUSION_UNKNOWN",
                        "severity": "warning",
                        "explanation_de": "Ohne eindeutige Einordnung zum Basisziel wird kein automatischer Aufschlag vorgeschlagen.",
                        "date": day,
                        "suggested_action_de": "Wähle keine oder eine ausdrücklich manuelle Anpassung.",
                    }
                )
        elif payload.strategy.value == "custom_manual":
            delta = selected_energy or Decimal(0)
            cap = engine.effective_cap(
                baseline, pref.positive_energy_cap_kcal, pref.relative_energy_cap
            )
            negative_cap = min(pref.negative_energy_cap_kcal, baseline * pref.relative_energy_cap)
            if delta > cap or delta < -negative_cap or baseline + delta < floor:
                raise error(
                    "TRAINING_ADJUSTMENT_INVALID_CUSTOM_VALUE",
                    "Die manuelle Anpassung überschreitet eine Grenze oder unterschreitet das sichere Ausgangsminimum.",
                )
            suggested_min = suggested_max = Decimal(0)
        else:
            delta = suggested_min = suggested_max = Decimal(0)
            cap = Decimal(0)
        carb_low, carb_high = (
            rules.CARB_RANGES[category]
            if pref.carbohydrate_adjustments_enabled and items
            else (Decimal(0), Decimal(0))
        )
        carb_delta = payload.selected_carbohydrate_deltas.get(
            day.isoformat(), (carb_low + carb_high) / 2 if delta > 0 else Decimal(0)
        )
        if carb_delta < Decimal("-50") or carb_delta > Decimal("100"):
            raise error(
                "TRAINING_ADJUSTMENT_INVALID_CUSTOM_VALUE",
                "Der Kohlenhydrat-Schwerpunkt liegt außerhalb der Planungsgrenzen.",
            )
        adjusted_carb = dict(carb)
        if carb.get("available") and carb.get("value") is not None:
            adjusted_carb["value"] = str(Decimal(str(carb["value"])) + carb_delta)
            for key in ("minimum", "maximum"):
                if carb.get(key) is not None:
                    adjusted_carb[key] = str(Decimal(str(carb[key])) + carb_delta)
        metadata = {
            "session_ids": [str(item.id) for item in items],
            "session_versions": {str(item.id): item.version for item in items},
            "load_points": str(classification["points"]),
            "load_rule_version": rules.RULE_VERSION,
            "rule_identifier": rules.RULE_IDENTIFIER,
            "baseline_inclusion": sorted({item.baseline_inclusion for item in items}),
            "effective_cap_kcal": str(cap),
            "planning_assumption_de": "Temporäre Planungshilfe; kein gemessener Trainingsverbrauch.",
        }
        day_results.append(
            {
                "date": day,
                "session_count": len(items),
                "sessions": [row(item) for item in items],
                "load_category": category,
                "baseline_energy_target_kcal": baseline,
                "suggested_energy_delta_min_kcal": suggested_min,
                "suggested_energy_delta_max_kcal": suggested_max,
                "selected_energy_delta_kcal": delta,
                "adjusted_energy_target_kcal": baseline + delta,
                "carbohydrate_delta_min_g": carb_low,
                "carbohydrate_delta_max_g": carb_high,
                "selected_carbohydrate_delta_g": carb_delta,
                "baseline_carbohydrate_target": carb,
                "adjusted_carbohydrate_target": adjusted_carb,
                "protein_target": protein,
                "consistency": {
                    "energy_delta_kcal": delta,
                    "carbohydrate_delta_g": carb_delta,
                    "energy_represented_by_carbohydrate_kcal": carb_delta * 4,
                    "remaining_unallocated_energy_kcal": delta - carb_delta * 4,
                },
                "calculation_metadata": metadata,
                "warnings": [],
            }
        )
    overlaps = list(
        db.scalars(
            select(TrainingDayTargetAdjustment).where(
                TrainingDayTargetAdjustment.owner_profile_id == owner,
                TrainingDayTargetAdjustment.adjustment_date >= start,
                TrainingDayTargetAdjustment.adjustment_date <= end,
                TrainingDayTargetAdjustment.is_active.is_(True),
            )
        )
    )
    plans = plan_repository.in_date_range(db, owner, start, end)
    state = {
        "sessions": {str(item.id): item.version for item in sessions},
        "overlaps": {str(item.id): str(item.created_at) for item in overlaps},
        "plans": {
            str(item.plan_date): {
                "id": str(item.id),
                "assessment_id": str(item.assessment_id),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in plans
            if not item.is_archived
        },
    }
    weekly_baseline = baseline * Decimal(len(dates))
    weekly_adjusted = sum(
        (Decimal(str(item["adjusted_energy_target_kcal"])) for item in day_results), Decimal(0)
    )
    body = {
        "scope": payload.scope,
        "start_date": start,
        "end_date": end,
        "source_assessment": {
            "id": assessment.id,
            "calculated_at": assessment.calculated_at,
            "is_calibrated_revision": assessment.derivation_type == "energy_calibration",
            "baseline_energy_target_kcal": baseline,
        },
        "preference_id": pref.id,
        "preference_updated_at": pref.updated_at,
        "strategy": payload.strategy.value,
        "days": day_results,
        "weekly_summary": {
            "baseline_weekly_energy_kcal": weekly_baseline,
            "adjusted_weekly_energy_kcal": weekly_adjusted,
            "weekly_difference_kcal": weekly_adjusted - weekly_baseline,
            "balanced": abs(weekly_adjusted - weekly_baseline) < Decimal("0.01"),
        },
        "existing_adjustments": [row(item) for item in overlaps],
        "plan_state": state["plans"],
        "warnings": warnings,
        "rule_identifier": rules.RULE_IDENTIFIER,
        "rule_version": rules.RULE_VERSION,
        "calculated_at": datetime.now(UTC),
        "freshness_state": state,
        "notice_de": "Temporäre Zielanpassung für die Planung; kein gemessener Trainingsverbrauch und keine automatische Zieländerung.",
    }
    serial = encode(body)
    token_basis = {key: value for key, value in serial.items() if key != "calculated_at"}
    canonical = json.dumps(token_basis, sort_keys=True, separators=(",", ":"))
    serial["preview_token"] = hashlib.sha256(canonical.encode()).hexdigest()
    return serial


def apply(db: Session, owner: UUID, payload: ApplyRequest) -> dict[str, Any]:
    duplicate = db.scalar(
        select(TrainingAdjustmentBatch)
        .where(
            TrainingAdjustmentBatch.owner_profile_id == owner,
            TrainingAdjustmentBatch.client_operation_id == payload.client_operation_id,
        )
        .options(selectinload(TrainingAdjustmentBatch.adjustments))
    )
    if duplicate:
        return batch_detail(duplicate)
    current = preview(db, owner, payload.preview)
    if current["preview_token"] != payload.preview_token:
        raise error(
            "TRAINING_ADJUSTMENT_PREVIEW_STALE",
            "Die Datengrundlage hat sich geändert. Bitte prüfe eine neue Vorschau.",
            409,
        )
    overlap_ids = {UUID(str(item["id"])) for item in current["existing_adjustments"]}
    confirmed = set(payload.replacement_confirmation_ids)
    if not overlap_ids <= confirmed:
        raise error(
            "TRAINING_ADJUSTMENT_OVERLAP_CONFIRMATION_REQUIRED",
            "Für mindestens einen Tag existiert bereits eine Anpassung. Das Ersetzen muss bestätigt werden.",
            409,
        )
    assessment_id = UUID(str(current["source_assessment"]["id"]))
    now = datetime.now(UTC)
    snapshot = {key: value for key, value in current.items() if key != "preview_token"}
    batch = TrainingAdjustmentBatch(
        owner_profile_id=owner,
        scope=current["scope"],
        strategy=current["strategy"],
        source_assessment_id=assessment_id,
        preference_id=UUID(str(current["preference_id"])),
        iso_week_start=date.fromisoformat(current["start_date"])
        if current["scope"] == "iso_week"
        else None,
        single_date=date.fromisoformat(current["start_date"])
        if current["scope"] == "single_day"
        else None,
        rule_version=rules.RULE_VERSION,
        status="active",
        client_operation_id=payload.client_operation_id,
        preview_snapshot=snapshot,
        finalized_at=now,
    )
    db.add(batch)
    db.flush()
    old_batches: set[UUID] = set()
    for old in db.scalars(
        select(TrainingDayTargetAdjustment).where(TrainingDayTargetAdjustment.id.in_(overlap_ids))
    ):
        old.is_active = False
        old.superseded_at = now
        old_batches.add(old.batch_id)
    for old_batch in db.scalars(
        select(TrainingAdjustmentBatch).where(TrainingAdjustmentBatch.id.in_(old_batches))
    ):
        old_batch.status = "superseded"
        old_batch.superseded_at = now
    created: dict[date, TrainingDayTargetAdjustment] = {}
    for value in current["days"]:
        day = date.fromisoformat(value["date"])
        item = TrainingDayTargetAdjustment(
            batch_id=batch.id,
            owner_profile_id=owner,
            adjustment_date=day,
            source_assessment_id=assessment_id,
            strategy=current["strategy"],
            load_category=value["load_category"],
            baseline_energy_target_kcal=Decimal(value["baseline_energy_target_kcal"]),
            energy_delta_kcal=Decimal(value["selected_energy_delta_kcal"]),
            adjusted_energy_target_kcal=Decimal(value["adjusted_energy_target_kcal"]),
            carbohydrate_delta_g=Decimal(value["selected_carbohydrate_delta_g"]),
            baseline_carbohydrate_target_snapshot=value["baseline_carbohydrate_target"],
            adjusted_carbohydrate_target_snapshot=value["adjusted_carbohydrate_target"],
            protein_target_snapshot=value["protein_target"],
            safety_validation_status="valid",
            calculation_metadata=value["calculation_metadata"],
            is_active=True,
        )
        db.add(item)
        created[day] = item
    db.flush()
    link_dates = set(payload.link_to_daily_plan_dates) | set(payload.create_missing_plan_dates)
    for day in link_dates:
        if day not in created:
            raise error(
                "TRAINING_ADJUSTMENT_PLAN_DATE_INVALID",
                "Ein gewählter Tagesplan liegt außerhalb der Vorschau.",
            )
        plan = plan_repository.by_date(db, owner, day)
        if plan is None:
            if day not in payload.create_missing_plan_dates:
                raise error(
                    "DAILY_PLAN_NOT_FOUND", "Der gewählte Tagesplan wurde nicht gefunden.", 404
                )
            plan = DailyMealPlan(owner_profile_id=owner, plan_date=day, assessment_id=assessment_id)
            db.add(plan)
        elif plan.assessment_id != assessment_id:
            raise error(
                "TRAINING_ADJUSTMENT_PLAN_ASSESSMENT_CONFLICT",
                "Die Anpassung basiert auf einem anderen Assessment als dieser Tagesplan.",
                409,
            )
        plan.training_day_adjustment_id = created[day].id
    db.commit()
    db.refresh(batch)
    return batch_detail(batch)


def batch_detail(batch: TrainingAdjustmentBatch) -> dict[str, Any]:
    result = row(batch)
    result["adjustments"] = [
        row(item) for item in sorted(batch.adjustments, key=lambda x: x.adjustment_date)
    ]
    return result


def list_adjustments(
    db: Session, owner: UUID, start: date | None = None, end: date | None = None
) -> list[dict]:
    query = (
        select(TrainingAdjustmentBatch)
        .where(TrainingAdjustmentBatch.owner_profile_id == owner)
        .options(selectinload(TrainingAdjustmentBatch.adjustments))
    )
    if start:
        query = query.where(
            (TrainingAdjustmentBatch.single_date >= start)
            | (TrainingAdjustmentBatch.iso_week_start >= start - timedelta(days=6))
        )
    return [
        batch_detail(item)
        for item in db.scalars(query.order_by(TrainingAdjustmentBatch.created_at.desc())).unique()
    ]


def cancel_adjustment(db: Session, owner: UUID, adjustment_id: UUID) -> dict:
    item = db.scalar(
        select(TrainingDayTargetAdjustment).where(
            TrainingDayTargetAdjustment.id == adjustment_id,
            TrainingDayTargetAdjustment.owner_profile_id == owner,
        )
    )
    if item is None:
        raise error(
            "TRAINING_ADJUSTMENT_NOT_FOUND", "Die Tagesanpassung wurde nicht gefunden.", 404
        )
    item.is_active = False
    item.superseded_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return row(item)


def link_plan(
    db: Session, owner: UUID, adjustment_id: UUID, plan_id: UUID | None, create: bool
) -> dict:
    adjustment = db.scalar(
        select(TrainingDayTargetAdjustment).where(
            TrainingDayTargetAdjustment.id == adjustment_id,
            TrainingDayTargetAdjustment.owner_profile_id == owner,
        )
    )
    if adjustment is None:
        raise error(
            "TRAINING_ADJUSTMENT_NOT_FOUND", "Die Tagesanpassung wurde nicht gefunden.", 404
        )
    plan = (
        plan_repository.get(db, owner, plan_id)
        if plan_id
        else plan_repository.by_date(db, owner, adjustment.adjustment_date)
    )
    if plan is None and create:
        plan = DailyMealPlan(
            owner_profile_id=owner,
            plan_date=adjustment.adjustment_date,
            assessment_id=adjustment.source_assessment_id,
        )
        db.add(plan)
    if plan is None:
        raise error("DAILY_PLAN_NOT_FOUND", "Der Tagesplan wurde nicht gefunden.", 404)
    if (
        plan.plan_date != adjustment.adjustment_date
        or plan.assessment_id != adjustment.source_assessment_id
    ):
        raise error(
            "TRAINING_ADJUSTMENT_PLAN_ASSESSMENT_CONFLICT",
            "Datum oder Assessment des Tagesplans stimmen nicht mit der Anpassung überein.",
            409,
        )
    plan.training_day_adjustment_id = adjustment.id
    db.commit()
    db.refresh(plan)
    return {"linked": True, "plan_id": str(plan.id), "adjustment_id": str(adjustment.id)}


def unlink_plan(db: Session, owner: UUID, plan_id: UUID) -> dict:
    plan = plan_repository.get(db, owner, plan_id)
    if plan is None:
        raise error("DAILY_PLAN_NOT_FOUND", "Der Tagesplan wurde nicht gefunden.", 404)
    previous = plan.training_day_adjustment_id
    plan.training_day_adjustment_id = None
    db.commit()
    return {
        "unlinked": True,
        "plan_id": str(plan.id),
        "adjustment_id": None if previous is None else str(previous),
    }
