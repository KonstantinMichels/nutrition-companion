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
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.modules.consumption_tracking import service as consumption_service
from app.modules.consumption_tracking.enums import Completeness, DayStatus
from app.modules.consumption_tracking.models import ConsumptionDay, ConsumptionMeal
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

from . import engine, intake_engine, rules
from .models import (
    EnergyCalibrationConsumptionEvidence,
    EnergyCalibrationRecord,
    EnergyCalibrationWeightEvidence,
)
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


def _target_response_preview(
    session: Session, owner: UUID, payload: PreviewRequest
) -> dict[str, Any]:
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
        "method": "target_response_proxy",
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


def _source_components(source: Assessment) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    energy = source.summary["energy_target"]
    assert isinstance(energy, dict)
    lower, midpoint, upper = (Decimal(str(energy[key])) for key in ("lower", "midpoint", "upper"))
    tdee = next(
        (
            m.raw_value
            for m in source.metrics
            if m.metric_code == "energy.maintenance" and m.raw_value is not None
        ),
        None,
    )
    if tdee is None:
        raise ApiError(
            "INTAKE_CALIBRATION_ASSESSMENT_UNSUPPORTED",
            "Die Einschätzung enthält keine nutzbare Ausgangsschätzung des Energieverbrauchs.",
            409,
        )
    return tdee, midpoint - tdee, lower, midpoint, upper


def _consumption_days(
    session: Session, owner: UUID, start: date, end: date
) -> list[ConsumptionDay]:
    return list(
        session.scalars(
            select(ConsumptionDay)
            .where(
                ConsumptionDay.owner_profile_id == owner,
                ConsumptionDay.consumption_date >= start,
                ConsumptionDay.consumption_date <= end,
            )
            .options(selectinload(ConsumptionDay.meals).selectinload(ConsumptionMeal.entries))
        )
    )


def _classify_day(day: ConsumptionDay, payload: PreviewRequest) -> dict[str, object]:
    quality = consumption_service._quality(day)
    totals = consumption_service._totals(day)
    energy = next((item for item in totals if item["nutrient_code"] == "energy_kcal"), None)
    amount = None if energy is None else energy["amount"]
    state, explanation = "usable", "Der finalisierte Tag besitzt vollständige Energiedaten."
    if day.id in payload.excluded_consumption_day_ids or (
        payload.included_consumption_day_ids and day.id not in payload.included_consumption_day_ids
    ):
        state, explanation = "excluded_user", "Für diese Vorschau ausdrücklich ausgeschlossen."
    elif day.status != DayStatus.FINALIZED:
        state, explanation = "excluded_open", "Der Verzehrtag ist noch offen."
    elif day.completeness_attestation == Completeness.PARTIAL:
        state, explanation = (
            "excluded_partial",
            "Der Tag wurde als teilweise vollständig abgeschlossen.",
        )
    elif day.completeness_attestation == Completeness.UNCERTAIN:
        state, explanation = "excluded_uncertain", "Die Vollständigkeit des Tages ist unsicher."
    elif day.completeness_attestation != Completeness.COMPLETE:
        state, explanation = (
            "excluded_incomplete",
            "Es fehlt die Bestätigung der vollständigen Aufzeichnung.",
        )
    elif quality["unresolved_entry_count"]:
        state, explanation = (
            "excluded_unresolved",
            "Mindestens ein manueller Eintrag besitzt keine auflösbaren Energiedaten.",
        )
    elif amount is None or energy is None or not energy["is_complete"]:
        state, explanation = (
            "excluded_missing_energy",
            "Die Energieaufnahme ist nicht vollständig bekannt.",
        )
    elif quality["estimated_conversion_count"] or quality["source_changed_count"]:
        state, explanation = (
            "conditionally_usable",
            "Die Energie ist vollständig, enthält aber eine geschätzte Umrechnung "
            "oder Quellenwarnung.",
        )
        if day.id in payload.conditional_day_confirmations:
            state, explanation = (
                "usable",
                "Bedingte Aufnahme wurde für diese Vorschau ausdrücklich bestätigt.",
            )
    return {
        "id": str(day.id),
        "date": day.consumption_date.isoformat(),
        "version": day.version,
        "finalized_at": None if day.finalized_at is None else day.finalized_at.isoformat(),
        "status": day.status,
        "completeness_attestation": day.completeness_attestation,
        "recorded_energy_kcal": amount,
        "energy_coverage": None if energy is None else energy["coverage_ratio"],
        "unresolved_count": quality["unresolved_entry_count"],
        "estimated_conversion_count": quality["estimated_conversion_count"],
        "eligibility_state": state,
        "explanation_de": explanation,
        "exclusion_reason": payload.consumption_exclusion_reasons.get(day.id),
    }


def _intake_preview(session: Session, owner: UUID, payload: PreviewRequest) -> dict[str, Any]:
    if payload.window_end > date.today():
        raise ApiError(
            "INTAKE_CALIBRATION_FUTURE_WINDOW",
            "Das Ende des Zeitraums darf nicht in der Zukunft liegen.",
            422,
        )
    span = (payload.window_end - payload.window_start).days + 1
    if (
        payload.window_start >= payload.window_end
        or not rules.MIN_WINDOW_DAYS <= span <= rules.MAX_WINDOW_DAYS
    ):
        raise ApiError(
            "INTAKE_CALIBRATION_INVALID_WINDOW", "Der Zeitraum muss 21 bis 90 Tage umfassen.", 422
        )
    source = _source(session, owner, payload.source_assessment_id)
    source_tdee, goal_adjustment, lower, midpoint, upper = _source_components(source)
    days = _consumption_days(session, owner, payload.window_start, payload.window_end)
    known_day_ids = {day.id for day in days}
    requested_day_ids = (
        set(payload.included_consumption_day_ids)
        | set(payload.excluded_consumption_day_ids)
        | set(payload.conditional_day_confirmations)
    )
    if not requested_day_ids <= known_day_ids:
        raise ApiError(
            "INTAKE_CALIBRATION_CONSUMPTION_DAY_NOT_FOUND",
            "Mindestens ein ausgewählter Verzehrtag ist nicht verfügbar.",
            404,
        )
    classified = [_classify_day(day, payload) for day in days]
    included = [item for item in classified if item["eligibility_state"] == "usable"]
    coverage_values, intake_checks = intake_engine.coverage(
        [date.fromisoformat(str(item["date"])) for item in included],
        payload.window_start,
        payload.window_end,
    )
    checks: list[dict[str, object]] = [
        {
            "code": "source_assessment_usable",
            "passed": True,
            "current": True,
            "required": True,
            "explanation_de": "Die Ausgangseinschätzung ist nutzbar.",
        },
        {
            "code": "minimum_window_length_met",
            "passed": span >= rules.MIN_WINDOW_DAYS,
            "current": span,
            "required": rules.MIN_WINDOW_DAYS,
            "explanation_de": "Der Zeitraum umfasst mindestens 21 Tage.",
        },
        {
            "code": "maximum_window_length_met",
            "passed": span <= rules.MAX_WINDOW_DAYS,
            "current": span,
            "required": rules.MAX_WINDOW_DAYS,
            "explanation_de": "Der Zeitraum umfasst höchstens 90 Tage.",
        },
        *intake_checks,
    ]
    confidence_ok = payload.recording_confidence in {"high", "moderate"}
    routine_ok = payload.routine_representativeness in {"representative", "minor_changes"}
    checks += [
        {
            "code": "recording_confidence_eligible",
            "passed": confidence_ok,
            "current": payload.recording_confidence,
            "required": "high_or_moderate",
            "explanation_de": "Die Aufzeichnungsqualität muss hoch oder moderat sein.",
        },
        {
            "code": "routine_representativeness_eligible",
            "passed": routine_ok,
            "current": payload.routine_representativeness,
            "required": "representative_or_minor_changes",
            "explanation_de": "Der Zeitraum muss den üblichen Alltag ausreichend abbilden.",
        },
    ]
    raw_points = _points(session, owner)
    requested_weight = set(payload.included_weight_observation_ids)
    excluded_weight = set(payload.excluded_weight_observation_ids)
    known_weight_ids = {UUID(point.id) for point in raw_points}
    if not (requested_weight | excluded_weight) <= known_weight_ids:
        raise ApiError(
            "INTAKE_CALIBRATION_WEIGHT_OBSERVATION_NOT_FOUND",
            "Mindestens ein ausgewählter Gewichtswert ist nicht verfügbar.",
            404,
        )
    selected_points = [
        p
        for p in raw_points
        if payload.window_start <= p.day <= payload.window_end
        and UUID(p.id) not in excluded_weight
        and (not requested_weight or UUID(p.id) in requested_weight)
    ]
    weight_evaluation = engine.evaluate_window(
        selected_points, payload.window_start, payload.window_end
    )
    trend_evidence = weight_evaluation.evidence["trend"]
    assert isinstance(trend_evidence, dict)
    for code, passed, current, required, explanation in (
        (
            "minimum_weight_days_met",
            len(selected_points) >= rules.MIN_REPRESENTATIVE_DAYS,
            len(selected_points),
            rules.MIN_REPRESENTATIVE_DAYS,
            "Mindestens acht repräsentative Gewichtstage.",
        ),
        (
            "weight_trend_quality_met",
            weight_evaluation.eligible,
            trend_evidence.get("quality_level"),
            "usable",
            "Der Gewichtsverlauf muss auswertbar sein.",
        ),
    ):
        checks.append(
            {
                "code": code,
                "passed": passed,
                "current": current,
                "required": required,
                "explanation_de": explanation,
            }
        )
    previous = session.scalar(
        select(EnergyCalibrationRecord)
        .where(
            EnergyCalibrationRecord.owner_profile_id == owner,
            EnergyCalibrationRecord.method == "intake_informed",
            EnergyCalibrationRecord.status == "accepted",
        )
        .order_by(EnergyCalibrationRecord.created_at.desc())
        .limit(1)
    )
    new_intake_days = (
        len(included)
        if previous is None
        else sum(date.fromisoformat(str(item["date"])) > previous.window_end for item in included)
    )
    new_weight_days = (
        len(selected_points)
        if previous is None
        else sum(point.day > previous.window_end for point in selected_points)
    )
    cooldown_days = None if previous is None else (date.today() - previous.created_at.date()).days
    new_span = None if previous is None else (payload.window_end - previous.window_end).days
    overlap_days = (
        0
        if previous is None
        else max(
            0,
            (
                min(payload.window_end, previous.window_end)
                - max(payload.window_start, previous.window_start)
            ).days
            + 1,
        )
    )
    for code, passed, current, required, explanation in (
        (
            "cooldown_met",
            previous is None
            or (cooldown_days is not None and cooldown_days >= rules.CALIBRATION_COOLDOWN_DAYS),
            cooldown_days,
            rules.CALIBRATION_COOLDOWN_DAYS,
            "Zwischen übernommenen Kalibrierungen liegen mindestens 21 Tage.",
        ),
        (
            "new_usable_intake_days_met",
            previous is None or new_intake_days >= rules.MIN_NEW_INTAKE_DAYS,
            new_intake_days,
            rules.MIN_NEW_INTAKE_DAYS,
            "Seit der letzten Kalibrierung sind mindestens sieben neue Verzehrtage nötig.",
        ),
        (
            "new_weight_representative_days_met",
            previous is None or new_weight_days >= rules.MIN_NEW_WEIGHT_DAYS,
            new_weight_days,
            rules.MIN_NEW_WEIGHT_DAYS,
            "Seit der letzten Kalibrierung sind mindestens fünf neue Gewichtstage nötig.",
        ),
        (
            "new_evidence_requirement_met",
            previous is None or (new_span is not None and new_span >= rules.MIN_NEW_CALENDAR_SPAN),
            new_span,
            rules.MIN_NEW_CALENDAR_SPAN,
            "Das Fensterende muss mindestens 14 Tage neue Kalenderzeit umfassen.",
        ),
    ):
        checks.append(
            {
                "code": code,
                "passed": passed,
                "current": current,
                "required": required,
                "explanation_de": explanation,
            }
        )
    eligible = all(bool(item["passed"]) for item in checks)
    intake: dict[str, object] = {**coverage_values, "days": classified}
    calculation: dict[str, object] = {}
    proposal: dict[str, object] | None = None
    if included:
        intake.update(
            intake_engine.intake_summary(
                [Decimal(str(item["recorded_energy_kcal"])) for item in included],
                payload.recording_confidence,
                payload.routine_representativeness,
            )
        )
        low_fence, high_fence = (
            Decimal(str(intake["unusual_lower_fence_kcal"])),
            Decimal(str(intake["unusual_upper_fence_kcal"])),
        )
        intake["unusual_days"] = [
            {
                "id": item["id"],
                "date": item["date"],
                "recorded_energy_kcal": item["recorded_energy_kcal"],
                "explanation_de": (
                    "Dieser Tag unterscheidet sich deutlich von den übrigen erfassten "
                    "Tagen. Bitte prüfe, ob er für den Zeitraum repräsentativ ist."
                ),
            }
            for item in included
            if Decimal(str(item["recorded_energy_kcal"])) < low_fence
            or Decimal(str(item["recorded_energy_kcal"])) > high_fence
        ]
    if eligible:
        calculation, proposal = intake_engine.calculate(
            intake=intake,
            trend=weight_evaluation.evidence["trend"],
            source_tdee=source_tdee,
            source_goal_adjustment=goal_adjustment,
            source_lower=lower,
            source_upper=upper,
            confidence=payload.recording_confidence,
            routine=payload.routine_representativeness,
        )
    body: dict[str, Any] = {
        "method": "intake_informed",
        "source_assessment_id": str(source.id),
        "source_assessment": {
            "id": str(source.id),
            "estimated_tdee_kcal": source_tdee,
            "goal_adjustment_kcal": goal_adjustment,
            "effective_energy_target_kcal": midpoint,
            "target_lower_kcal": lower,
            "target_upper_kcal": upper,
        },
        "window": {
            "start": payload.window_start.isoformat(),
            "end": payload.window_end.isoformat(),
            "calendar_day_count": span,
            "overlap_calendar_days": overlap_days,
            "new_usable_intake_days": new_intake_days,
            "new_weight_representative_days": new_weight_days,
        },
        "eligibility": {"eligible": eligible, "checks": checks},
        "blockers": [item["code"] for item in checks if not item["passed"]],
        "intake_evidence": intake,
        "weight_evidence": weight_evaluation.evidence,
        "calculation": calculation,
        "proposal": proposal,
        "recording_confidence": payload.recording_confidence,
        "routine_representativeness": payload.routine_representativeness,
        "rule_set": rules.RULE_SET_ID,
        "rule_version": rules.INTAKE_RULE_SET_VERSION,
        "warnings": [
            {
                "code": "SELF_REPORTED_INTAKE",
                "severity": "information",
                "message_de": (
                    "Die Aufnahme basiert auf selbst berichteten, finalisierten "
                    "Verzehrdaten und ist keine objektive Messung."
                ),
            }
        ],
        "calculated_at": datetime.now(UTC).isoformat(),
        "notice_de": (
            "Die Schätzung misst weder die tatsächliche Energieaufnahme noch den "
            "tatsächlichen Energieverbrauch und ist nicht diagnostisch."
        ),
    }
    canonical = json.dumps(_json(body), sort_keys=True, separators=(",", ":"))
    body["preview_token"] = hashlib.sha256(canonical.encode()).hexdigest()
    return _json(body)  # type: ignore[return-value]


def preview(session: Session, owner: UUID, payload: PreviewRequest) -> dict[str, Any]:
    return (
        _intake_preview(session, owner, payload)
        if payload.method == "intake_informed"
        else _target_response_preview(session, owner, payload)
    )


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


def eligible_windows(
    session: Session, owner: UUID, method: str = "target_response_proxy"
) -> dict[str, Any]:
    points = _points(session, owner)
    if not points:
        return {"items": []}
    end = min(points[-1].day, date.today())
    items = []
    for days in (28, 35, 42, 21, 56, 90):
        start = end - timedelta(days=days - 1)
        evaluation = engine.evaluate_window(points, start, end)
        if method == "intake_informed":
            try:
                result = _intake_preview(
                    session,
                    owner,
                    PreviewRequest(
                        method="intake_informed",
                        window_start=start,
                        window_end=end,
                        recording_confidence="high",
                        routine_representativeness="representative",
                    ),
                )
                item = {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "window_days": days,
                    "eligible": result["eligibility"]["eligible"],
                    "blockers": result["blockers"],
                    "preferred": rules.PREFERRED_MIN_DAYS
                    <= days
                    <= rules.INTAKE_PREFERRED_MAX_DAYS,
                    "usable_intake_days": result["intake_evidence"].get("usable_day_count", 0),
                    "coverage_ratio": result["intake_evidence"].get("coverage_ratio", "0"),
                    "representative_days": result["weight_evidence"]["representative_days"],
                }
                items.append(item)
                continue
            except ApiError:
                pass
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
    proposal = preview_data.get("proposal") or {}
    assert isinstance(proposal, dict)
    intake_method = preview_data.get("method") == "intake_informed"
    evidence = preview_data["weight_evidence"] if intake_method else preview_data["evidence"]
    window = preview_data.get("window", {})
    record = EnergyCalibrationRecord(
        owner_profile_id=owner,
        client_operation_id=operation_id,
        source_assessment_id=UUID(str(preview_data["source_assessment_id"])),
        status=status,
        method=str(preview_data.get("method", "target_response_proxy")),
        window_start=date.fromisoformat(str(window.get("start", evidence["start_date"]))),
        window_end=date.fromisoformat(str(window.get("end", evidence["end_date"]))),
        adherence=str(preview_data.get("adherence", "not_applicable")),
        context_stability=str(preview_data.get("context_stability", "not_applicable")),
        proposed_adjustment_kcal_per_day=Decimal(str(proposal["proposed_adjustment_kcal_per_day"]))
        if proposal.get("available")
        else None,
        accepted_adjustment_kcal_per_day=accepted,
        evidence_snapshot={
            "intake": preview_data.get("intake_evidence"),
            "weight": evidence,
            "eligibility": preview_data.get("eligibility"),
            "recording_confidence": preview_data.get("recording_confidence"),
            "routine_representativeness": preview_data.get("routine_representativeness"),
        }
        if intake_method
        else evidence,
        proposal_snapshot=proposal,
        rules_snapshot={
            "identifier": rules.RULE_SET_ID,
            "version": preview_data.get("rule_version", rules.RULE_SET_VERSION),
            "energy_equivalent_kcal_per_kg": ["6500", "7700", "9500"],
            "deadband": "75",
            "absolute_cap": "200",
            "relative_cap": "0.10",
        },
    )
    session.add(record)
    session.flush()
    if intake_method:
        for item in preview_data["intake_evidence"]["days"]:
            session.add(
                EnergyCalibrationConsumptionEvidence(
                    calibration_record_id=record.id,
                    source_id=UUID(item["id"]),
                    source_version_snapshot=int(item["version"]),
                    included=item["eligibility_state"] == "usable",
                    exclusion_reason=item.get("exclusion_reason")
                    or (
                        None if item["eligibility_state"] == "usable" else item["eligibility_state"]
                    ),
                    evidence_date=date.fromisoformat(item["date"]),
                    recorded_value_snapshot=None
                    if item["recorded_energy_kcal"] is None
                    else Decimal(str(item["recorded_energy_kcal"])),
                    evidence_snapshot=item,
                )
            )
        included_ids = set(preview_data["weight_evidence"]["observation_ids"])
        for point in _points(session, owner):
            if record.window_start <= point.day <= record.window_end:
                session.add(
                    EnergyCalibrationWeightEvidence(
                        calibration_record_id=record.id,
                        source_id=UUID(point.id),
                        included=point.id in included_ids,
                        exclusion_reason=None
                        if point.id in included_ids
                        else "excluded_from_preview",
                        evidence_date=point.day,
                        recorded_value_snapshot=point.value,
                        evidence_snapshot={
                            "observation_id": point.id,
                            "date": point.day.isoformat(),
                            "weight_kg": str(point.value),
                        },
                    )
                )
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
    raw_input = source.input_snapshot.get("engine_input", {})
    previous_value = (
        raw_input.get("energy_calibration_adjustment_kcal_per_day")
        if isinstance(raw_input, dict)
        else None
    )
    previous = Decimal(0) if previous_value is None else Decimal(str(previous_value))
    cumulative_adjustment = previous + adjustment
    result = calculate_assessment(
        _rebuild_input(source, cumulative_adjustment), calculated_at=timestamp
    )
    serialized = result.to_dict()
    input_snapshot = dict(source.input_snapshot)
    input_snapshot["engine_input"] = serialized["input_snapshot"]
    input_snapshot["energy_calibration"] = {
        "record_id": str(record.id),
        "source_assessment_id": str(source.id),
        "adjustment_kcal_per_day": str(adjustment),
        "cumulative_adjustment_kcal_per_day": str(cumulative_adjustment),
        "method": record.method,
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


def history(session: Session, owner: UUID, method: str | None = None) -> list[dict[str, Any]]:
    query = select(EnergyCalibrationRecord).where(EnergyCalibrationRecord.owner_profile_id == owner)
    if method:
        query = query.where(EnergyCalibrationRecord.method == method)
    rows = session.scalars(query.order_by(EnergyCalibrationRecord.created_at.desc())).all()
    return [serialize(row) for row in rows]
