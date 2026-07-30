from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.nutrition_assessment import repository
from app.modules.nutrition_assessment.engine import (
    AssessmentInput,
    EngineInputError,
    HealthScreening,
    Measurement,
    NutritionGoal,
    SportActivity,
    calculate_assessment,
)
from app.modules.nutrition_assessment.models import Assessment, AssessmentMetric, SafetyFlag
from app.modules.nutrition_assessment.schemas import (
    AssessmentHistoryItem,
    AssessmentHistoryResponse,
)
from app.modules.privacy.service import require_assessment_consent
from app.modules.profiles import repository as profile_repository
from app.modules.profiles.models import Profile
from app.modules.progress_tracking.models import BodyWeightObservation
from app.modules.reference_data import repository as reference_repository


def _age_on(birth_date: date, on_date: date) -> int:
    return (
        on_date.year
        - birth_date.year
        - ((on_date.month, on_date.day) < (birth_date.month, birth_date.day))
    )


def _complete_profile_or_error(session: Session, profile_id: UUID) -> Profile:
    profile = profile_repository.get_profile(session, profile_id)
    if profile is None:
        raise ApiError(
            code="PROFILE_NOT_FOUND",
            message="Speichere zuerst dein Profil.",
            status_code=404,
        )
    missing: list[dict[str, str]] = []
    for field, value, message in (
        ("activity", profile.activity_profile, "Bitte ergänze deine Alltagsaktivität."),
        ("goal", profile.goal, "Bitte wähle ein Ziel."),
        (
            "health_screening",
            profile.health_screening,
            "Bitte beantworte die Fragen zur Gesundheitssituation.",
        ),
    ):
        if value is None:
            missing.append({"field": field, "code": "REQUIRED", "message": message})
    if missing:
        raise ApiError(
            code="PROFILE_INCOMPLETE",
            message="Für die Auswertung fehlen noch Angaben.",
            status_code=409,
            field_errors=missing,
        )
    return profile


def _engine_measurement(profile: Profile, measurement_type: str) -> Measurement | None:
    record = next(
        (item for item in profile.measurements if item.measurement_type == measurement_type),
        None,
    )
    if record is None:
        return None
    return Measurement(
        value=record.value,
        unit=record.unit,
        measured_at=record.measured_at,
        source_type=record.source_type,
    )


def _engine_input(profile: Profile, calculated_at: datetime) -> AssessmentInput:
    activity = profile.activity_profile
    goal = profile.goal
    screening = profile.health_screening
    assert activity is not None and goal is not None and screening is not None
    return AssessmentInput(
        age_years=_age_on(profile.birth_date, calculated_at.date()),
        height_cm=profile.height_cm,
        weight_kg=profile.current_weight_kg,
        physiological_category=profile.physiological_category,
        activity_category=activity.occupational_activity_category,
        goal=NutritionGoal(
            goal_type=goal.goal_type,
            desired_intensity=goal.desired_intensity,
            target_weight_kg=goal.target_weight_kg,
            requested_weekly_rate_kg=goal.requested_weekly_rate_kg,
        ),
        sports=tuple(
            SportActivity(
                sport_type=sport.sport_type,
                sessions_per_week=sport.sessions_per_week,
                minutes_per_session=sport.minutes_per_session,
                intensity=sport.intensity,
                note=sport.note,
            )
            for sport in activity.sports
        ),
        manual_pal_override=activity.manual_pal_override,
        body_fat_percentage=_engine_measurement(profile, "body_fat_percentage"),
        waist_circumference=_engine_measurement(profile, "waist_circumference"),
        hip_circumference=_engine_measurement(profile, "hip_circumference"),
        measured_resting_energy_expenditure=_engine_measurement(
            profile, "measured_resting_energy_expenditure"
        ),
        health_screening=HealthScreening(
            pregnant=screening.pregnant,
            breastfeeding=screening.breastfeeding,
            diagnosed_eating_disorder=screening.diagnosed_eating_disorder,
            diabetes=screening.diabetes,
            kidney_disease=screening.kidney_disease,
            liver_disease=screening.liver_disease,
            medically_prescribed_diet=screening.medically_prescribed_diet,
            serious_metabolic_condition=screening.serious_metabolic_condition,
            other_professional_nutrition_condition=(
                screening.other_professional_nutrition_condition
            ),
        ),
        dietary_preference=profile.dietary_preference,
    )


def _complete_snapshot(
    profile: Profile,
    engine_snapshot: dict[str, Any],
    *,
    consent_id: UUID,
    consent_text_version: str,
) -> dict[str, Any]:
    activity = profile.activity_profile
    return {
        "engine_input": engine_snapshot,
        "profile": {
            "birth_date": profile.birth_date.isoformat(),
            "dietary_preference": profile.dietary_preference,
            "preferred_meals_per_day": profile.preferred_meals_per_day,
            "preferred_meal_timing": profile.preferred_meal_timing,
        },
        "daily_activity_context": {
            "average_daily_steps": activity.average_daily_steps if activity else None,
            "active_commuting": activity.active_commuting if activity else None,
            "movement_notes": activity.movement_notes if activity else None,
        },
        "dietary_restrictions": [
            {
                "restriction_type": item.restriction_type,
                "value": item.value,
                "hard_exclusion": item.hard_exclusion,
                "note": item.note,
            }
            for item in profile.restrictions
        ],
        "health_screening_note": (
            profile.health_screening.user_note if profile.health_screening else None
        ),
        "consent": {
            "consent_record_id": str(consent_id),
            "consent_text_version": consent_text_version,
            "purpose_code": "nutrition_assessment_calculation",
        },
    }


def create_assessment(
    session: Session,
    profile_id: UUID,
    client_request_id: UUID,
    *,
    calculated_at: datetime | None = None,
) -> Assessment:
    duplicate = repository.get_by_client_request(session, profile_id, client_request_id)
    if duplicate is not None:
        return duplicate

    profile = _complete_profile_or_error(session, profile_id)
    consent = require_assessment_consent(session, profile_id)
    reference_set = reference_repository.current_reference_set(session)
    rule_set = reference_repository.current_application_rule_set(session)
    if reference_set is None or rule_set is None:
        raise ApiError(
            code="REFERENCE_DATA_NOT_SEEDED",
            message="Die Referenz- und Regelwerte sind noch nicht initialisiert.",
            status_code=503,
        )

    timestamp = calculated_at or datetime.now(UTC)
    try:
        engine_input = _engine_input(profile, timestamp)
        result = calculate_assessment(engine_input, calculated_at=timestamp)
    except EngineInputError as error:
        raise ApiError(
            code="VALIDATION_ERROR",
            message="Die Eingaben konnten nicht verarbeitet werden.",
            status_code=422,
            field_errors=[
                {"field": item.field, "code": item.code, "message": item.message_de}
                for item in error.issues
            ],
        ) from None

    if (
        result.reference_set_identifier != reference_set.identifier
        or result.reference_set_version != reference_set.version
        or result.application_rule_set_identifier != rule_set.identifier
        or result.application_rule_set_version != rule_set.version
    ):
        raise ApiError(
            code="REFERENCE_VERSION_MISMATCH",
            message="Die Berechnungskonfiguration ist inkonsistent. Es wurde nichts gespeichert.",
            status_code=503,
        )

    # Persist the engine's explicit JSON representation. This keeps the database
    # adapter safe if a future summary or snapshot field contains Decimal/date/
    # Enum values, while numeric metric columns retain their Decimal precision.
    serialized_result = result.to_dict()
    snapshot = _complete_snapshot(
        profile,
        cast(dict[str, Any], serialized_result["input_snapshot"]),
        consent_id=consent.id,
        consent_text_version=consent.consent_text_version,
    )
    assessment = Assessment(
        profile_id=profile_id,
        client_request_id=client_request_id,
        input_snapshot=snapshot,
        supported_scope_status=result.supported_scope_status.value,
        reference_set_id=reference_set.id,
        application_rule_set_id=rule_set.id,
        reference_set_identifier=result.reference_set_identifier,
        reference_set_version=result.reference_set_version,
        application_rule_set_identifier=result.application_rule_set_identifier,
        application_rule_set_version=result.application_rule_set_version,
        engine_version=result.engine_version,
        calculated_at=result.calculated_at,
        summary=cast(dict[str, object], serialized_result["summary"]),
    )
    assessment.metrics.extend(
        AssessmentMetric(**metric.to_persistence_dict()) for metric in result.metrics
    )
    assessment.safety_flags.extend(
        SafetyFlag(
            code=flag.code,
            severity=flag.severity.value,
            explanation_de=flag.explanation_de,
            recommended_action_de=flag.recommended_action_de,
        )
        for flag in result.safety_flags
    )
    try:
        session.add(assessment)
        session.flush()
        local_timestamp = result.calculated_at.astimezone(ZoneInfo("Europe/Berlin"))
        session.add(
            BodyWeightObservation(
                owner_profile_id=profile_id,
                observed_on=local_timestamp.date(),
                observed_time=local_timestamp.time().replace(tzinfo=None),
                normalized_weight_kg=engine_input.weight_kg,
                entered_weight=engine_input.weight_kg,
                entered_unit="kg",
                source_type="assessment",
                source_assessment_id=assessment.id,
                measurement_context="unspecified",
                note=None,
                unusual_change_confirmed=False,
            )
        )
        session.commit()
        # Return exactly the precision persisted by the database, including on the
        # first POST response rather than the pre-flush in-memory Decimal objects.
        session.expire_all()
    except IntegrityError:
        session.rollback()
        concurrent_duplicate = repository.get_by_client_request(
            session, profile_id, client_request_id
        )
        if concurrent_duplicate is not None:
            return concurrent_duplicate
        raise
    except Exception:
        session.rollback()
        raise

    stored = repository.get_assessment(session, profile_id, assessment.id)
    assert stored is not None
    return stored


def require_assessment(session: Session, profile_id: UUID, assessment_id: UUID) -> Assessment:
    assessment = repository.get_assessment(session, profile_id, assessment_id)
    if assessment is None:
        raise ApiError(
            code="ASSESSMENT_NOT_FOUND",
            message="Die Auswertung wurde nicht gefunden.",
            status_code=404,
        )
    return assessment


def require_latest_assessment(session: Session, profile_id: UUID) -> Assessment:
    assessment = repository.latest_assessment(session, profile_id)
    if assessment is None:
        raise ApiError(
            code="ASSESSMENT_NOT_FOUND",
            message="Es liegt noch keine Auswertung vor.",
            status_code=404,
        )
    return assessment


def assessment_history(
    session: Session, profile_id: UUID, *, limit: int, offset: int
) -> AssessmentHistoryResponse:
    assessments, total = repository.list_assessments(
        session, profile_id, limit=limit, offset=offset
    )
    items = []
    for assessment in assessments:
        energy = assessment.summary.get("energy_target", {})
        energy_summary = None
        if isinstance(energy, dict) and energy.get("available"):
            energy_summary = (
                f"{energy.get('lower')} bis {energy.get('upper')} {energy.get('unit', 'kcal/Tag')}"
            )
        items.append(
            AssessmentHistoryItem(
                id=assessment.id,
                calculated_at=assessment.calculated_at,
                supported_scope_status=assessment.supported_scope_status,
                goal_type=str(assessment.summary.get("goal_type", "unknown")),
                energy_target_summary=energy_summary,
                warning_codes=[flag.code for flag in assessment.safety_flags],
            )
        )
    return AssessmentHistoryResponse(items=items, limit=limit, offset=offset, total=total)
