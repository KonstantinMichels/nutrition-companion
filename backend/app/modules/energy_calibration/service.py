# mypy: disable-error-code="arg-type,dict-item"
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.nutrition_assessment.engine import (
    AssessmentInput,
    HealthScreening,
    Measurement,
    NutritionGoal,
    SportActivity,
    calculate_assessment,
)
from app.modules.nutrition_assessment.models import Assessment, AssessmentMetric, SafetyFlag
from app.modules.progress_tracking.engine import WeightPoint, representatives
from app.modules.progress_tracking.models import BodyWeightObservation

from . import engine, rules
from .models import EnergyCalibrationRecord
from .schemas import PreviewRequest


def _source(session: Session, owner: UUID, requested: UUID | None = None) -> Assessment:
    query = select(Assessment).where(Assessment.profile_id == owner)
    if requested:
        query = query.where(Assessment.id == requested)
    item = session.scalar(query.order_by(Assessment.calculated_at.desc()).limit(1))
    if item is None:
        raise ApiError(
            "ENERGY_CALIBRATION_SOURCE_NOT_FOUND", "Es liegt keine passende Einschätzung vor.", 404
        )
    energy = item.summary.get("energy_target", {})
    if not isinstance(energy, dict) or not energy.get("available"):
        raise ApiError(
            "ENERGY_CALIBRATION_SOURCE_UNAVAILABLE",
            "Die Einschätzung enthält kein nutzbares Energie-Ziel.",
            409,
        )
    return item


def _points(session: Session, owner: UUID) -> list[WeightPoint]:
    rows = session.scalars(
        select(BodyWeightObservation)
        .where(BodyWeightObservation.owner_profile_id == owner)
        .order_by(BodyWeightObservation.observed_on, BodyWeightObservation.created_at)
    ).all()
    return representatives(
        [
            WeightPoint(
                str(row.id), row.observed_on, row.normalized_weight_kg, row.observed_time, index
            )
            for index, row in enumerate(rows)
        ]
    )


def _expected_balance(source: Assessment) -> Decimal:
    maintenance = next(
        (
            metric.raw_value
            for metric in source.metrics
            if metric.metric_code == "energy.maintenance" and metric.raw_value is not None
        ),
        None,
    )
    energy = source.summary.get("energy_target", {})
    if maintenance is not None and isinstance(energy, dict) and energy.get("midpoint") is not None:
        # The source engine's conservative goal adjustment, not an asserted true
        # deficit/surplus, is the expected balance used by calibration.
        return Decimal(str(energy["midpoint"])) - maintenance
    snapshot = source.input_snapshot.get("engine_input", {})
    goal = snapshot.get("goal", {}) if isinstance(snapshot, dict) else {}
    goal_type = goal.get("goal_type") if isinstance(goal, dict) else None
    rate_value = goal.get("requested_weekly_rate_kg") if isinstance(goal, dict) else None
    if rate_value is not None:
        rate = Decimal(str(rate_value)) * rules.ENERGY_EQUIVALENT_CENTRAL / Decimal(7)
        return (
            -abs(rate)
            if goal_type == "lose_weight"
            else abs(rate)
            if goal_type == "gain_weight"
            else Decimal(0)
        )
    return Decimal(0)


def _json(value: object) -> object:
    return jsonable_encoder(value, custom_encoder={Decimal: str})


def preview(session: Session, owner: UUID, payload: PreviewRequest) -> dict[str, Any]:
    source = _source(session, owner, payload.source_assessment_id)
    evaluation = engine.evaluate_window(
        _points(session, owner), payload.window_start, payload.window_end
    )
    energy = source.summary["energy_target"]
    assert isinstance(energy, dict)
    lower, midpoint, upper = (Decimal(str(energy[key])) for key in ("lower", "midpoint", "upper"))
    result: dict[str, object] = {"available": False, "reason": "EVIDENCE_INSUFFICIENT"}
    if evaluation.eligible:
        result = engine.proposal(
            trend=evaluation.evidence["trend"],
            assumed_intake=midpoint,
            expected_balance=_expected_balance(source),
            source_lower=lower,
            source_upper=upper,
            adherence=payload.adherence,
            context=payload.context_stability,
        )
    latest_record = session.scalar(
        select(EnergyCalibrationRecord)
        .where(EnergyCalibrationRecord.owner_profile_id == owner)
        .order_by(EnergyCalibrationRecord.created_at.desc())
        .limit(1)
    )
    body = {
        "source_assessment_id": str(source.id),
        "source_calculated_at": source.calculated_at.isoformat(),
        "source_target": {"lower": str(lower), "midpoint": str(midpoint), "upper": str(upper)},
        "evidence": _json(evaluation.evidence),
        "blockers": list(evaluation.blockers),
        "adherence": payload.adherence,
        "context_stability": payload.context_stability,
        "proposal": _json(result),
        "rule_set": rules.RULE_SET_ID,
        "rule_version": rules.RULE_SET_VERSION,
        "latest_calibration_state": (
            {"id": str(latest_record.id), "status": latest_record.status} if latest_record else None
        ),
        "notice_de": (
            "Die Schätzung basiert auf dem Gewichtsverlauf und deinen Angaben. "
            "Sie misst weder die tatsächliche Energieaufnahme noch den Energieverbrauch."
        ),
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["preview_token"] = hashlib.sha256(canonical.encode()).hexdigest()
    return body


def eligibility(session: Session, owner: UUID) -> dict[str, Any]:
    try:
        source = _source(session, owner)
    except ApiError as error:
        if error.code in {
            "ENERGY_CALIBRATION_SOURCE_NOT_FOUND",
            "ENERGY_CALIBRATION_SOURCE_UNAVAILABLE",
        }:
            return {
                "eligible": False,
                "blockers": [error.code],
                "source_assessment_id": None,
                "representative_days": len(_points(session, owner)),
                "rule_version": rules.RULE_SET_VERSION,
            }
        raise
    points = _points(session, owner)
    latest = points[-1].day if points else date.today()
    evaluation = engine.evaluate_window(points, latest - timedelta(days=27), latest)
    return {
        "eligible": evaluation.eligible,
        "blockers": list(evaluation.blockers),
        "source_assessment_id": str(source.id),
        "representative_days": len(points),
        "rule_version": rules.RULE_SET_VERSION,
    }


def eligible_windows(session: Session, owner: UUID) -> dict[str, Any]:
    points = _points(session, owner)
    if not points:
        return {"items": []}
    end = points[-1].day
    items = []
    for days in (28, 35, 42, 21, 56, 90):
        evaluation = engine.evaluate_window(points, end - timedelta(days=days - 1), end)
        items.append(
            {
                **_json(evaluation.evidence),
                "eligible": evaluation.eligible,
                "blockers": list(evaluation.blockers),
                "preferred": rules.PREFERRED_MIN_DAYS <= days <= rules.PREFERRED_MAX_DAYS,
            }
        )
    return {"items": items}


def persist(
    session: Session,
    owner: UUID,
    operation_id: UUID,
    preview_data: dict[str, Any],
    *,
    status: str,
    accepted: Decimal | None = None,
) -> EnergyCalibrationRecord:
    duplicate = session.scalar(
        select(EnergyCalibrationRecord).where(
            EnergyCalibrationRecord.owner_profile_id == owner,
            EnergyCalibrationRecord.client_operation_id == operation_id,
        )
    )
    if duplicate:
        return duplicate
    proposal = preview_data["proposal"]
    assert isinstance(proposal, dict)
    record = EnergyCalibrationRecord(
        owner_profile_id=owner,
        client_operation_id=operation_id,
        source_assessment_id=UUID(str(preview_data["source_assessment_id"])),
        status=status,
        window_start=date.fromisoformat(str(preview_data["evidence"]["start_date"])),
        window_end=date.fromisoformat(str(preview_data["evidence"]["end_date"])),
        adherence=str(preview_data["adherence"]),
        context_stability=str(preview_data["context_stability"]),
        proposed_adjustment_kcal_per_day=Decimal(str(proposal["proposed_adjustment_kcal_per_day"]))
        if proposal.get("available")
        else None,
        accepted_adjustment_kcal_per_day=accepted,
        evidence_snapshot=preview_data["evidence"],
        proposal_snapshot=proposal,
        rules_snapshot={
            "identifier": rules.RULE_SET_ID,
            "version": rules.RULE_SET_VERSION,
            "energy_equivalent_kcal_per_kg": ["6500", "7700", "9500"],
            "deadband": "75",
            "absolute_cap": "200",
            "relative_cap": "0.10",
        },
    )
    session.add(record)
    return record


def serialize(record: EnergyCalibrationRecord) -> dict[str, Any]:
    return _json({column.name: getattr(record, column.name) for column in record.__table__.columns})  # type: ignore[return-value]


def _measurement(value: object) -> Measurement | None:
    if not isinstance(value, dict):
        return None
    return Measurement(
        value=str(value["value"]),
        unit=str(value["unit"]),
        measured_at=date.fromisoformat(str(value["measured_at"])),
        source_type=str(value["source_type"]),
    )


def _rebuild_input(source: Assessment, adjustment: Decimal) -> AssessmentInput:
    raw = source.input_snapshot["engine_input"]
    assert isinstance(raw, dict)
    goal = raw["goal"]
    assert isinstance(goal, dict)
    screening = raw.get("health_screening", {})
    assert isinstance(screening, dict)
    sports = raw.get("sports", [])
    assert isinstance(sports, list)
    return AssessmentInput(
        age_years=int(raw["age_years"]),
        height_cm=str(raw["height_cm"]),
        weight_kg=str(raw["weight_kg"]),
        physiological_category=str(raw["physiological_category"]),
        activity_category=str(raw["activity_category"]),
        goal=NutritionGoal(
            goal_type=str(goal["goal_type"]),
            desired_intensity=goal.get("desired_intensity"),
            target_weight_kg=goal.get("target_weight_kg"),
            requested_weekly_rate_kg=goal.get("requested_weekly_rate_kg"),
        ),
        sports=tuple(
            SportActivity(
                sport_type=str(item["sport_type"]),
                sessions_per_week=str(item["sessions_per_week"]),
                minutes_per_session=str(item["minutes_per_session"]),
                intensity=str(item["intensity"]),
                note=item.get("note"),
            )
            for item in sports
            if isinstance(item, dict)
        ),
        manual_pal_override=raw.get("manual_pal_override"),
        body_fat_percentage=_measurement(raw.get("body_fat_percentage")),
        waist_circumference=_measurement(raw.get("waist_circumference")),
        hip_circumference=_measurement(raw.get("hip_circumference")),
        measured_resting_energy_expenditure=_measurement(
            raw.get("measured_resting_energy_expenditure")
        ),
        health_screening=HealthScreening(**screening),
        dietary_preference=str(raw["dietary_preference"]),
        energy_calibration_adjustment_kcal_per_day=adjustment,
    )


def create_revision(
    session: Session, owner: UUID, record: EnergyCalibrationRecord, adjustment: Decimal
) -> Assessment:
    source = _source(session, owner, record.source_assessment_id)
    timestamp = datetime.now(UTC)
    result = calculate_assessment(_rebuild_input(source, adjustment), calculated_at=timestamp)
    serialized = result.to_dict()
    input_snapshot = dict(source.input_snapshot)
    input_snapshot["engine_input"] = serialized["input_snapshot"]
    input_snapshot["energy_calibration"] = {
        "record_id": str(record.id),
        "source_assessment_id": str(source.id),
        "adjustment_kcal_per_day": str(adjustment),
    }
    assessment = Assessment(
        profile_id=owner,
        client_request_id=uuid4(),
        input_snapshot=input_snapshot,
        supported_scope_status=result.supported_scope_status.value,
        reference_set_id=source.reference_set_id,
        application_rule_set_id=source.application_rule_set_id,
        reference_set_identifier=result.reference_set_identifier,
        reference_set_version=result.reference_set_version,
        application_rule_set_identifier=result.application_rule_set_identifier,
        application_rule_set_version=result.application_rule_set_version,
        engine_version=result.engine_version,
        calculated_at=timestamp,
        summary=serialized["summary"],
        derived_from_assessment_id=source.id,
        derivation_type="energy_calibration",
        energy_calibration_record_id=record.id,
        energy_calibration_adjustment_kcal_per_day=adjustment,
    )
    assessment.metrics.extend(
        AssessmentMetric(**item.to_persistence_dict()) for item in result.metrics
    )
    assessment.safety_flags.extend(
        SafetyFlag(
            code=item.code,
            severity=item.severity.value,
            explanation_de=item.explanation_de,
            recommended_action_de=item.recommended_action_de,
        )
        for item in result.safety_flags
    )
    session.add(assessment)
    session.flush()
    record.created_assessment_id = assessment.id
    return assessment


def history(session: Session, owner: UUID) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(EnergyCalibrationRecord)
        .where(EnergyCalibrationRecord.owner_profile_id == owner)
        .order_by(EnergyCalibrationRecord.created_at.desc())
    ).all()
    return [serialize(row) for row in rows]
