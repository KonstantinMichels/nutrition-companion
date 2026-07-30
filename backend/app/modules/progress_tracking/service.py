from __future__ import annotations

# mypy: disable-error-code="type-arg,no-any-return,var-annotated"
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.database.base import utc_now
from app.modules.progress_tracking import engine
from app.modules.progress_tracking.models import (
    BodyCompositionObservation,
    BodyMeasurementObservation,
    BodyWeightObservation,
    ProgressGoal,
)
from app.modules.progress_tracking.schemas import (
    CompositionWrite,
    GoalWrite,
    MeasurementWrite,
    WeightWrite,
)

LB_TO_KG = Decimal("0.45359237")
IN_TO_CM = Decimal("2.54")
WEIGHT_MIN, WEIGHT_MAX = Decimal(20), Decimal(500)
CIRC_MIN, CIRC_MAX = Decimal(10), Decimal(400)
UNUSUAL_THRESHOLD = Decimal("0.05")


def _future(day: date) -> None:
    if day > date.today():
        raise ApiError(
            "PROGRESS_FUTURE_DATE_NOT_ALLOWED", "Messungen in der Zukunft sind nicht möglich.", 422
        )


def _version(item: Any, expected: int | None) -> None:
    if expected is not None and item.version != expected:
        raise ApiError(
            "PROGRESS_CONCURRENT_MODIFICATION",
            "Der Eintrag wurde zwischenzeitlich geändert. Bitte lade ihn neu.",
            409,
        )


def _get(session: Session, model: Any, owner: UUID, item_id: UUID, code: str) -> Any:
    item = session.scalar(select(model).where(model.id == item_id, model.owner_profile_id == owner))
    if item is None:
        raise ApiError(code, "Der Fortschrittseintrag wurde nicht gefunden.", 404)
    return item


def _dict(item: Any) -> dict[str, Any]:
    return jsonable_encoder(
        {column.name: getattr(item, column.name) for column in item.__table__.columns},
        custom_encoder={Decimal: str},
    )


def _weight_kg(value: Decimal, unit: str) -> Decimal:
    normalized = value if unit == "kg" else value * LB_TO_KG
    if not WEIGHT_MIN <= normalized <= WEIGHT_MAX:
        raise ApiError(
            "PROGRESS_INVALID_WEIGHT",
            "Das Gewicht liegt außerhalb der breiten Eingabegrenzen von 20 bis 500 kg.",
            422,
        )
    return normalized


def _unusual(
    session: Session, owner: UUID, day: date, value: Decimal, exclude: UUID | None = None
) -> bool:
    query = select(BodyWeightObservation).where(
        BodyWeightObservation.owner_profile_id == owner, BodyWeightObservation.observed_on <= day
    )
    if exclude:
        query = query.where(BodyWeightObservation.id != exclude)
    previous = session.scalars(
        query.order_by(
            BodyWeightObservation.observed_on.desc(),
            BodyWeightObservation.observed_time.desc().nullslast(),
            BodyWeightObservation.created_at.desc(),
        ).limit(1)
    ).first()
    return bool(
        previous
        and (day - previous.observed_on).days <= 7
        and abs(value - previous.normalized_weight_kg) / previous.normalized_weight_kg
        >= UNUSUAL_THRESHOLD
    )


def create_weight(session: Session, owner: UUID, payload: WeightWrite) -> dict:
    _future(payload.observed_on)
    value = _weight_kg(payload.entered_weight, payload.entered_unit)
    unusual = _unusual(session, owner, payload.observed_on, value)
    if unusual and not payload.confirm_unusual_change:
        raise ApiError(
            "PROGRESS_PLAUSIBILITY_CONFIRMATION_REQUIRED",
            "Dieser Wert unterscheidet sich deutlich vom letzten Eintrag. Bitte prüfe die Eingabe.",
            409,
        )
    item = BodyWeightObservation(
        owner_profile_id=owner,
        observed_on=payload.observed_on,
        observed_time=payload.observed_time,
        normalized_weight_kg=value,
        entered_weight=payload.entered_weight,
        entered_unit=payload.entered_unit,
        measurement_context=payload.measurement_context,
        source_type="manual",
        note=payload.note,
        unusual_change_confirmed=unusual,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return _dict(item)


def update_weight(session: Session, owner: UUID, item_id: UUID, payload: WeightWrite) -> dict:
    item = _get(
        session, BodyWeightObservation, owner, item_id, "PROGRESS_WEIGHT_OBSERVATION_NOT_FOUND"
    )
    _version(item, payload.expected_version)
    _future(payload.observed_on)
    value = _weight_kg(payload.entered_weight, payload.entered_unit)
    unusual = _unusual(session, owner, payload.observed_on, value, item_id)
    if unusual and not payload.confirm_unusual_change:
        raise ApiError(
            "PROGRESS_PLAUSIBILITY_CONFIRMATION_REQUIRED",
            "Dieser Wert unterscheidet sich deutlich vom letzten Eintrag. Bitte prüfe die Eingabe.",
            409,
        )
    for key, value_ in {
        "observed_on": payload.observed_on,
        "observed_time": payload.observed_time,
        "normalized_weight_kg": value,
        "entered_weight": payload.entered_weight,
        "entered_unit": payload.entered_unit,
        "measurement_context": payload.measurement_context,
        "note": payload.note,
        "unusual_change_confirmed": unusual,
    }.items():
        setattr(item, key, value_)
    item.version += 1
    session.commit()
    session.refresh(item)
    return _dict(item)


def _paged(
    session: Session,
    model: Any,
    owner: UUID,
    date_from: date | None,
    date_to: date | None,
    page: int,
    page_size: int,
    sort: str,
    extra: Any = None,
) -> dict:
    conditions = [model.owner_profile_id == owner]
    if date_from:
        conditions.append(model.observed_on >= date_from)
    if date_to:
        conditions.append(model.observed_on <= date_to)
    if extra is not None:
        conditions.append(extra)
    ordering = (
        model.observed_on.asc()
        if sort == "observed_at_asc"
        else model.created_at.desc()
        if sort == "created_at_desc"
        else model.observed_on.desc()
    )
    total = session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0
    items = session.scalars(
        select(model)
        .where(*conditions)
        .order_by(ordering, model.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_dict(i) for i in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def list_weights(session: Session, owner: UUID, **kwargs: Any) -> dict:
    return _paged(session, BodyWeightObservation, owner, **kwargs)


def weight_detail(session: Session, owner: UUID, item_id: UUID) -> dict:
    return _dict(
        _get(
            session, BodyWeightObservation, owner, item_id, "PROGRESS_WEIGHT_OBSERVATION_NOT_FOUND"
        )
    )


def delete_weight(
    session: Session, owner: UUID, item_id: UUID, expected_version: int | None
) -> dict:
    item = _get(
        session, BodyWeightObservation, owner, item_id, "PROGRESS_WEIGHT_OBSERVATION_NOT_FOUND"
    )
    _version(item, expected_version)
    session.delete(item)
    session.commit()
    return {"deleted": True, "id": str(item_id)}


def create_measurement(session: Session, owner: UUID, payload: MeasurementWrite) -> dict:
    _future(payload.observed_on)
    value = (
        payload.entered_value if payload.entered_unit == "cm" else payload.entered_value * IN_TO_CM
    )
    if not CIRC_MIN <= value <= CIRC_MAX:
        raise ApiError(
            "PROGRESS_INVALID_MEASUREMENT",
            "Der Umfang liegt außerhalb der breiten Eingabegrenzen von 10 bis 400 cm.",
            422,
        )
    item = BodyMeasurementObservation(
        owner_profile_id=owner,
        normalized_value_cm=value,
        source_type="manual",
        **payload.model_dump(exclude={"expected_version"}),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return _dict(item)


def update_measurement(
    session: Session, owner: UUID, item_id: UUID, payload: MeasurementWrite
) -> dict:
    item = _get(
        session, BodyMeasurementObservation, owner, item_id, "PROGRESS_BODY_MEASUREMENT_NOT_FOUND"
    )
    _version(item, payload.expected_version)
    _future(payload.observed_on)
    value = (
        payload.entered_value if payload.entered_unit == "cm" else payload.entered_value * IN_TO_CM
    )
    if not CIRC_MIN <= value <= CIRC_MAX:
        raise ApiError(
            "PROGRESS_INVALID_MEASUREMENT", "Der Umfang liegt außerhalb der Eingabegrenzen.", 422
        )
    for key, val in payload.model_dump(exclude={"expected_version"}).items():
        setattr(item, key, val)
    item.normalized_value_cm = value
    item.version += 1
    session.commit()
    session.refresh(item)
    return _dict(item)


def list_measurements(
    session: Session, owner: UUID, measurement_type: str | None = None, **kwargs: Any
) -> dict:
    extra = (
        BodyMeasurementObservation.measurement_type == measurement_type
        if measurement_type
        else None
    )
    return _paged(session, BodyMeasurementObservation, owner, extra=extra, **kwargs)


def measurement_detail(session: Session, owner: UUID, item_id: UUID) -> dict:
    return _dict(
        _get(
            session,
            BodyMeasurementObservation,
            owner,
            item_id,
            "PROGRESS_BODY_MEASUREMENT_NOT_FOUND",
        )
    )


def delete_measurement(
    session: Session, owner: UUID, item_id: UUID, expected_version: int | None
) -> dict:
    item = _get(
        session, BodyMeasurementObservation, owner, item_id, "PROGRESS_BODY_MEASUREMENT_NOT_FOUND"
    )
    _version(item, expected_version)
    session.delete(item)
    session.commit()
    return {"deleted": True, "id": str(item_id)}


def _validate_composition(payload: CompositionWrite) -> None:
    _future(payload.observed_on)
    bounds = (
        (payload.body_fat_percent, Decimal(1), Decimal(75)),
        (payload.lean_mass_kg, Decimal(5), Decimal(400)),
        (payload.fat_mass_kg, Decimal(0), Decimal(400)),
    )
    if any(value is not None and not low <= value <= high for value, low, high in bounds):
        raise ApiError(
            "PROGRESS_INVALID_BODY_COMPOSITION",
            "Mindestens ein Körperzusammensetzungswert liegt außerhalb der breiten Eingabegrenzen.",
            422,
        )


def create_composition(session: Session, owner: UUID, payload: CompositionWrite) -> dict:
    _validate_composition(payload)
    item = BodyCompositionObservation(
        owner_profile_id=owner,
        source_type="manual",
        **payload.model_dump(exclude={"expected_version"}),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return _dict(item)


def update_composition(
    session: Session, owner: UUID, item_id: UUID, payload: CompositionWrite
) -> dict:
    item = _get(
        session, BodyCompositionObservation, owner, item_id, "PROGRESS_BODY_COMPOSITION_NOT_FOUND"
    )
    _version(item, payload.expected_version)
    _validate_composition(payload)
    for key, val in payload.model_dump(exclude={"expected_version"}).items():
        setattr(item, key, val)
    item.version += 1
    session.commit()
    session.refresh(item)
    return _dict(item)


def list_composition(
    session: Session, owner: UUID, measurement_method: str | None = None, **kwargs: Any
) -> dict:
    extra = (
        BodyCompositionObservation.measurement_method == measurement_method
        if measurement_method
        else None
    )
    return _paged(session, BodyCompositionObservation, owner, extra=extra, **kwargs)


def composition_detail(session: Session, owner: UUID, item_id: UUID) -> dict:
    return _dict(
        _get(
            session,
            BodyCompositionObservation,
            owner,
            item_id,
            "PROGRESS_BODY_COMPOSITION_NOT_FOUND",
        )
    )


def delete_composition(
    session: Session, owner: UUID, item_id: UUID, expected_version: int | None
) -> dict:
    item = _get(
        session, BodyCompositionObservation, owner, item_id, "PROGRESS_BODY_COMPOSITION_NOT_FOUND"
    )
    _version(item, expected_version)
    session.delete(item)
    session.commit()
    return {"deleted": True, "id": str(item_id)}


def _validate_goal(payload: GoalWrite) -> None:
    if payload.target_date and payload.start_date > payload.target_date:
        raise ApiError(
            "PROGRESS_GOAL_INVALID_DATE", "Das Zieldatum darf nicht vor dem Startdatum liegen.", 422
        )
    point, low, high = (
        payload.target_weight_kg,
        payload.target_weight_min_kg,
        payload.target_weight_max_kg,
    )
    if point is not None and (low is not None or high is not None):
        raise ApiError(
            "PROGRESS_GOAL_INVALID_TARGET",
            "Bitte verwende entweder einen Zielwert oder einen Zielbereich.",
            422,
        )
    incomplete_range = (low is None) != (high is None)
    reversed_range = low is not None and high is not None and low > high
    if incomplete_range or reversed_range:
        raise ApiError(
            "PROGRESS_GOAL_INVALID_RANGE",
            "Bitte gib einen vollständigen, aufsteigenden Zielbereich ein.",
            422,
        )
    if payload.goal_type == "maintain_weight" and (low is None or high is None):
        raise ApiError(
            "PROGRESS_GOAL_INVALID_RANGE",
            "Für ein Erhaltungsziel ist ein Zielbereich erforderlich.",
            422,
        )
    if payload.goal_type in {"lose_weight", "gain_weight"} and point is None and low is None:
        raise ApiError(
            "PROGRESS_GOAL_INVALID_TARGET",
            "Für dieses Ziel ist ein Zielwert oder Zielbereich erforderlich.",
            422,
        )


def create_goal(session: Session, owner: UUID, payload: GoalWrite) -> dict:
    _validate_goal(payload)
    active = session.scalar(
        select(ProgressGoal).where(
            ProgressGoal.owner_profile_id == owner, ProgressGoal.status == "active"
        )
    )
    if active and not payload.replace_active:
        raise ApiError(
            "PROGRESS_GOAL_ALREADY_ACTIVE",
            "Es besteht bereits ein aktives Ziel. Bestätige, dass es ersetzt werden soll.",
            409,
        )
    if active:
        active.status = "replaced"
        active.replaced_at = utc_now()
        active.version += 1
    start, source = payload.start_weight_kg, None
    if payload.use_latest_weight:
        latest = session.scalars(
            select(BodyWeightObservation)
            .where(BodyWeightObservation.owner_profile_id == owner)
            .order_by(
                BodyWeightObservation.observed_on.desc(), BodyWeightObservation.created_at.desc()
            )
            .limit(1)
        ).first()
        if latest:
            start, source = latest.normalized_weight_kg, latest.id
    item = ProgressGoal(
        owner_profile_id=owner,
        goal_type=payload.goal_type,
        start_date=payload.start_date,
        start_weight_kg=start,
        start_observation_id=source,
        target_weight_kg=payload.target_weight_kg,
        target_weight_min_kg=payload.target_weight_min_kg,
        target_weight_max_kg=payload.target_weight_max_kg,
        target_date=payload.target_date,
        note=payload.note,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return _dict(item)


def list_goals(session: Session, owner: UUID) -> list[dict]:
    return [
        _dict(x)
        for x in session.scalars(
            select(ProgressGoal)
            .where(ProgressGoal.owner_profile_id == owner)
            .order_by(ProgressGoal.created_at.desc())
        ).all()
    ]


def goal_detail(session: Session, owner: UUID, goal_id: UUID) -> dict:
    return _dict(_get(session, ProgressGoal, owner, goal_id, "PROGRESS_GOAL_NOT_FOUND"))


def update_goal(session: Session, owner: UUID, goal_id: UUID, payload: GoalWrite) -> dict:
    item = _get(session, ProgressGoal, owner, goal_id, "PROGRESS_GOAL_NOT_FOUND")
    _version(item, payload.expected_version)
    _validate_goal(payload)
    for key in (
        "goal_type",
        "start_date",
        "start_weight_kg",
        "target_weight_kg",
        "target_weight_min_kg",
        "target_weight_max_kg",
        "target_date",
        "note",
    ):
        setattr(item, key, getattr(payload, key))
    item.version += 1
    session.commit()
    session.refresh(item)
    return _dict(item)


def set_goal_status(
    session: Session, owner: UUID, goal_id: UUID, status: str, expected_version: int | None
) -> dict:
    item = _get(session, ProgressGoal, owner, goal_id, "PROGRESS_GOAL_NOT_FOUND")
    _version(item, expected_version)
    if item.status != "active":
        raise ApiError(
            "PROGRESS_GOAL_NOT_ACTIVE",
            "Nur ein aktives Ziel kann abgeschlossen oder abgebrochen werden.",
            409,
        )
    item.status = status
    item.completed_at = utc_now() if status == "completed" else None
    item.version += 1
    session.commit()
    session.refresh(item)
    return _dict(item)


def _points(items: list[BodyWeightObservation]) -> list[engine.WeightPoint]:
    return engine.representatives(
        engine.WeightPoint(
            str(x.id),
            x.observed_on,
            x.normalized_weight_kg,
            x.observed_time,
            int(x.created_at.timestamp() * 1_000_000),
        )
        for x in items
    )


def overview(
    session: Session,
    owner: UUID,
    date_from: date | None,
    date_to: date | None,
    rolling_window_days: int,
) -> dict:
    end = date_to or date.today()
    start = date_from or end - timedelta(days=365)
    items = list(
        session.scalars(
            select(BodyWeightObservation)
            .where(
                BodyWeightObservation.owner_profile_id == owner,
                BodyWeightObservation.observed_on.between(start, end),
            )
            .order_by(BodyWeightObservation.observed_on, BodyWeightObservation.created_at)
        ).all()
    )
    reps = _points(items)
    roll = engine.rolling(reps, rolling_window_days)
    trend = engine.linear_trend(reps)
    latest_roll = next((x for x in reversed(roll) if x["value_kg"] is not None), None)
    latest = reps[-1] if reps else None
    goal = session.scalar(
        select(ProgressGoal).where(
            ProgressGoal.owner_profile_id == owner, ProgressGoal.status == "active"
        )
    )
    current = latest_roll["value_kg"] if latest_roll else latest.value if latest else None
    goal_result = _goal_progress(goal, current, bool(latest_roll)) if goal else None
    methods = set(
        session.scalars(
            select(BodyCompositionObservation.measurement_method).where(
                BodyCompositionObservation.owner_profile_id == owner
            )
        ).all()
    )
    duplicates = len(items) - len(reps)
    warnings = []
    if len(reps) < 3:
        warnings.append(
            {
                "code": "PROGRESS_TREND_INSUFFICIENT_DATA",
                "severity": "info",
                "explanation_de": (
                    "Für einen Trend werden mehrere Messungen über verschiedene Tage benötigt."
                ),
            }
        )
    if duplicates:
        warnings.append(
            {
                "code": "PROGRESS_MULTIPLE_SAME_DAY_MEASUREMENTS",
                "severity": "info",
                "explanation_de": (
                    "Mehrere Messwerte am selben Tag bleiben erhalten; für den Trend wird der "
                    "späteste verwendet."
                ),
            }
        )
    if len(methods) > 1:
        warnings.append(
            {
                "code": "PROGRESS_MIXED_BODY_COMPOSITION_METHODS",
                "severity": "warning",
                "explanation_de": (
                    "Werte verschiedener Messmethoden sind nur eingeschränkt direkt vergleichbar."
                ),
            }
        )
    chart = []
    by_day = {p.day: [] for p in reps}
    for item in items:
        by_day.setdefault(item.observed_on, []).append(
            {
                "observation_id": str(item.id),
                "time": item.observed_time,
                "value": item.normalized_weight_kg,
                "unit": "kg",
                "context": item.measurement_context,
                "source_type": item.source_type,
                "source_assessment_id": item.source_assessment_id,
            }
        )
    roll_by = {x["date"]: x for x in roll}
    for p in reps:
        chart.append(
            {
                "date": p.day,
                "raw_observations": by_day[p.day],
                "representative_value_kg": p.value,
                "rolling_average_kg": roll_by[p.day]["value_kg"],
                "rolling_observation_count": roll_by[p.day]["observation_count"],
            }
        )
    return jsonable_encoder(
        {
            "latest": {
                "raw_weight_kg": latest.value if latest else None,
                "raw_observed_on": latest.day if latest else None,
                "trend_weight_kg": latest_roll["value_kg"] if latest_roll else None,
                "trend_window_days": rolling_window_days,
                "trend_basis": "rolling_average"
                if latest_roll
                else "raw_fallback"
                if latest
                else "unavailable",
            },
            "active_goal": goal_result,
            "trend": trend,
            "interval_changes": engine.interval_changes(reps, end),
            "measurement_frequency": engine.frequency(reps, end),
            "data_quality": {
                "weight_observation_count": len(items),
                "representative_day_count": len(reps),
                "measurement_span_days": (reps[-1].day - reps[0].day).days if reps else 0,
                "rolling_average_available": latest_roll is not None,
                "linear_trend_available": trend["available"],
                "trend_quality_level": trend["quality_level"],
                "same_day_duplicate_count": duplicates,
                "unusual_change_warning_count": sum(x.unusual_change_confirmed for x in items),
                "mixed_composition_method_count": len(methods),
            },
            "warnings": warnings,
            "chart": {
                "same_day_policy": "latest",
                "rule_version": engine.RULE_VERSION,
                "points": chart,
            },
            "calculated_at": datetime.now(UTC),
        },
        custom_encoder={Decimal: str},
    )


def _goal_progress(goal: ProgressGoal, current: Decimal | None, rolling: bool) -> dict:
    relation = "unavailable"
    remaining = None
    ratio = None
    if (
        current is not None
        and goal.target_weight_min_kg is not None
        and goal.target_weight_max_kg is not None
    ):
        relation = (
            "below_target_range"
            if current < goal.target_weight_min_kg
            else "above_target_range"
            if current > goal.target_weight_max_kg
            else "within_target_range"
        )
        remaining = (
            goal.target_weight_min_kg - current
            if relation == "below_target_range"
            else current - goal.target_weight_max_kg
            if relation == "above_target_range"
            else Decimal(0)
        )
    elif current is not None and goal.target_weight_kg is not None:
        relation = "in_progress"
        remaining = abs(goal.target_weight_kg - current)
        if goal.start_weight_kg is not None and goal.start_weight_kg != goal.target_weight_kg:
            ratio = (current - goal.start_weight_kg) / (
                goal.target_weight_kg - goal.start_weight_kg
            )
    return {
        **_dict(goal),
        "current_weight_kg": current,
        "current_basis": "rolling_average_7_day" if rolling else "latest_raw",
        "remaining_change_kg": remaining,
        "progress_ratio": ratio,
        "relation": relation,
    }
