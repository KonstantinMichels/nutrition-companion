"""Authoritative engine-boundary validation driven by application rules."""

from __future__ import annotations

from datetime import datetime, timedelta

from .input_models import AssessmentInput, Measurement
from .result_models import EngineInputError, FieldIssue
from .rules import ApplicationRules


def validate_assessment_input(
    data: AssessmentInput, rules: ApplicationRules, calculated_at: datetime
) -> None:
    validation = rules.validation
    issues: list[FieldIssue] = []

    def issue(field: str, code: str, message: str) -> None:
        issues.append(FieldIssue(field=field, code=code, message_de=message))

    if not validation.age_minimum <= data.age_years <= validation.age_maximum:
        issue("age_years", "OUT_OF_RANGE", "Bitte gib ein plausibles Alter ein.")
    if not validation.height_cm_minimum_exclusive < data.height_cm <= validation.height_cm_maximum:
        issue("height_cm", "OUT_OF_RANGE", "Bitte gib eine plausible Körpergröße ein.")
    if not validation.weight_kg_minimum_exclusive < data.weight_kg <= validation.weight_kg_maximum:
        issue("weight_kg", "OUT_OF_RANGE", "Bitte gib ein plausibles Körpergewicht ein.")
    if data.manual_pal_override is not None and not (
        rules.pal.manual_override_minimum
        <= data.manual_pal_override
        <= rules.pal.manual_override_maximum
    ):
        issue(
            "manual_pal_override",
            "OUT_OF_RANGE",
            "Der manuelle PAL-Wert liegt außerhalb des erlaubten Bereichs.",
        )

    _validate_measurement(
        data.body_fat_percentage,
        field="body_fat_percentage",
        expected_unit="%",
        minimum=validation.body_fat_percent_minimum,
        maximum=validation.body_fat_percent_maximum,
        calculated_at=calculated_at,
        issues=issues,
    )
    _validate_measurement(
        data.waist_circumference,
        field="waist_circumference",
        expected_unit="cm",
        minimum=validation.circumference_cm_minimum,
        maximum=validation.circumference_cm_maximum,
        calculated_at=calculated_at,
        issues=issues,
    )
    _validate_measurement(
        data.hip_circumference,
        field="hip_circumference",
        expected_unit="cm",
        minimum=validation.circumference_cm_minimum,
        maximum=validation.circumference_cm_maximum,
        calculated_at=calculated_at,
        issues=issues,
    )
    _validate_measurement(
        data.measured_resting_energy_expenditure,
        field="measured_resting_energy_expenditure",
        expected_unit="kcal/day",
        minimum=validation.measured_ree_minimum,
        maximum=validation.measured_ree_maximum,
        calculated_at=calculated_at,
        issues=issues,
    )

    for index, sport in enumerate(data.sports):
        if sport.sessions_per_week > validation.sport_sessions_maximum:
            issue(
                f"sports.{index}.sessions_per_week",
                "OUT_OF_RANGE",
                "Die Anzahl der Sporteinheiten pro Woche ist nicht plausibel.",
            )
        if sport.minutes_per_session > validation.sport_minutes_per_session_maximum:
            issue(
                f"sports.{index}.minutes_per_session",
                "OUT_OF_RANGE",
                "Die Dauer einer Sporteinheit ist nicht plausibel.",
            )

    if data.goal.target_weight_kg is not None and not (
        validation.target_weight_kg_minimum_exclusive
        < data.goal.target_weight_kg
        <= validation.target_weight_kg_maximum
    ):
        issue(
            "goal.target_weight_kg",
            "OUT_OF_RANGE",
            "Bitte gib ein plausibles Zielgewicht ein.",
        )
    if data.goal.requested_weekly_rate_kg is not None and not (
        0 < data.goal.requested_weekly_rate_kg <= validation.requested_weekly_rate_kg_maximum
    ):
        issue(
            "goal.requested_weekly_rate_kg",
            "OUT_OF_RANGE",
            "Bitte gib eine plausible gewünschte wöchentliche Änderung ein.",
        )

    if issues:
        raise EngineInputError(tuple(issues))


def _validate_measurement(
    measurement: Measurement | None,
    *,
    field: str,
    expected_unit: str,
    minimum: object,
    maximum: object,
    calculated_at: datetime,
    issues: list[FieldIssue],
) -> None:
    if measurement is None:
        return
    if measurement.unit != expected_unit:
        issues.append(
            FieldIssue(
                field=f"{field}.unit",
                code="INVALID_UNIT",
                message_de=f"Für diese Messung wird die Einheit {expected_unit} erwartet.",
            )
        )
    if not minimum <= measurement.value <= maximum:  # type: ignore[operator]
        issues.append(
            FieldIssue(
                field=f"{field}.value",
                code="OUT_OF_RANGE",
                message_de="Der Messwert liegt außerhalb des plausiblen Bereichs.",
            )
        )
    if measurement.measured_at > calculated_at.date() + timedelta(days=1):
        issues.append(
            FieldIssue(
                field=f"{field}.measured_at",
                code="DATE_IN_FUTURE",
                message_de="Das Messdatum liegt zu weit in der Zukunft.",
            )
        )
