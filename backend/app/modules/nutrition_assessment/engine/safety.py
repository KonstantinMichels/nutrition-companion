"""Supported-scope classification and calm, non-diagnostic safety flags."""

from __future__ import annotations

from dataclasses import dataclass

from .input_models import AssessmentInput
from .result_models import SafetyFlag, SafetySeverity, SupportedScopeStatus


@dataclass(frozen=True, slots=True)
class ScopeAssessment:
    status: SupportedScopeStatus
    flags: tuple[SafetyFlag, ...]


_SCREENING_FLAGS: dict[str, tuple[str, str]] = {
    "pregnant": (
        "UNSUPPORTED_PREGNANCY",
        "Die automatische MVP-Berechnung ist nicht für eine Schwangerschaft ausgelegt.",
    ),
    "breastfeeding": (
        "UNSUPPORTED_BREASTFEEDING",
        "Die automatische MVP-Berechnung ist nicht für die Stillzeit ausgelegt.",
    ),
    "diagnosed_eating_disorder": (
        "UNSUPPORTED_EATING_DISORDER",
        "Bei einer angegebenen Essstörung erstellt das MVP keine normale Zielplanung.",
    ),
    "diabetes": (
        "UNSUPPORTED_DIABETES",
        "Bei angegebenem Diabetes erstellt das MVP keine medizinische Ernährungsplanung.",
    ),
    "kidney_disease": (
        "UNSUPPORTED_KIDNEY_DISEASE",
        "Bei einer angegebenen Nierenerkrankung ist eine individuelle fachliche Beurteilung nötig.",
    ),
    "liver_disease": (
        "UNSUPPORTED_LIVER_DISEASE",
        "Bei einer angegebenen Lebererkrankung ist eine individuelle fachliche Beurteilung nötig.",
    ),
    "medically_prescribed_diet": (
        "UNSUPPORTED_PRESCRIBED_DIET",
        "Eine medizinisch verordnete Ernährung liegt außerhalb des MVP-Anwendungsbereichs.",
    ),
    "serious_metabolic_condition": (
        "UNSUPPORTED_METABOLIC_CONDITION",
        "Die angegebene Stoffwechselsituation liegt außerhalb des MVP-Anwendungsbereichs.",
    ),
    "other_professional_nutrition_condition": (
        "UNSUPPORTED_PROFESSIONAL_CARE_CONDITION",
        "Die angegebene Situation erfordert eine individuelle professionelle Beurteilung.",
    ),
}


def assess_supported_scope(data: AssessmentInput) -> ScopeAssessment:
    flags: list[SafetyFlag] = []
    if not 18 <= data.age_years <= 65:
        flags.append(
            SafetyFlag(
                code="UNSUPPORTED_AGE",
                severity=SafetySeverity.BLOCKING,
                explanation_de=(
                    "Die automatische MVP-Berechnung unterstützt Erwachsene von 18 bis "
                    "einschließlich 65 Jahren."
                ),
                recommended_action_de=(
                    "Bitte nutze die Werte nicht als persönliche Empfehlung und wende dich bei "
                    "Bedarf an eine qualifizierte Fachperson."
                ),
            )
        )
    for field_name, (code, explanation) in _SCREENING_FLAGS.items():
        if getattr(data.health_screening, field_name):
            flags.append(
                SafetyFlag(
                    code=code,
                    severity=SafetySeverity.BLOCKING,
                    explanation_de=explanation,
                    recommended_action_de=(
                        "Bitte besprich persönliche Ernährungsziele mit einer qualifizierten "
                        "Ernährungsfachkraft oder ärztlichen Fachperson. Dies ist keine Diagnose."
                    ),
                )
            )
    status = SupportedScopeStatus.SUPPORTED if not flags else SupportedScopeStatus.UNSUPPORTED
    return ScopeAssessment(status=status, flags=tuple(flags))


def high_protein_kidney_flag() -> SafetyFlag:
    return SafetyFlag(
        code="HIGH_PROTEIN_KIDNEY_CONDITION",
        severity=SafetySeverity.BLOCKING,
        explanation_de=(
            "Ein sportbedingt erhöhter Proteinzielbereich wird wegen der angegebenen "
            "Nierenerkrankung nicht erzeugt."
        ),
        recommended_action_de=(
            "Bitte kläre die passende Proteinzufuhr individuell mit einer qualifizierten "
            "ärztlichen oder ernährungsmedizinischen Fachperson."
        ),
    )
