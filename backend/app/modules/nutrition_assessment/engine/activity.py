"""Transparent PAL mapping and documented handling of logged sport."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .input_models import AssessmentInput
from .rules import ApplicationRules


@dataclass(frozen=True, slots=True)
class PalCalculation:
    base_minimum: Decimal
    base_midpoint: Decimal
    base_maximum: Decimal
    sport_adjustment: Decimal
    final_minimum: Decimal
    final_midpoint: Decimal
    final_maximum: Decimal
    manual_override: Decimal | None
    total_weekly_exercise_minutes: Decimal
    qualifying_sessions: Decimal
    sport_was_added: bool
    final_range_was_capped: bool
    method_id: str
    explanation_de: str


def calculate_pal(data: AssessmentInput, rules: ApplicationRules) -> PalCalculation:
    band = rules.pal.categories[data.activity_category]
    total_minutes = data.total_weekly_exercise_minutes

    if data.manual_pal_override is not None:
        value = data.manual_pal_override
        return PalCalculation(
            base_minimum=band.minimum,
            base_midpoint=band.midpoint,
            base_maximum=band.maximum,
            sport_adjustment=Decimal(0),
            final_minimum=value,
            final_midpoint=value,
            final_maximum=value,
            manual_override=value,
            total_weekly_exercise_minutes=total_minutes,
            qualifying_sessions=Decimal(0),
            sport_was_added=False,
            final_range_was_capped=False,
            method_id="manual_pal_override_including_sport",
            explanation_de=(
                "Der manuell angegebene PAL-Wert wird als abschließender Gesamtwert verwendet. "
                "Protokollierter Sport wird deshalb nicht ein zweites Mal addiert."
            ),
        )

    qualifying_sessions = sum(
        (
            sport.sessions_per_week
            for sport in data.sports
            if sport.minutes_per_session >= rules.pal.minimum_minutes_per_session
            and sport.intensity.value in rules.pal.qualifying_intensities
        ),
        Decimal(0),
    )
    sport_is_qualifying = (
        not rules.pal.base_categories_include_logged_sport
        and qualifying_sessions >= rules.pal.minimum_qualifying_sessions
    )
    adjustment = rules.pal.sport_adjustment if sport_is_qualifying else Decimal(0)
    uncapped = (
        band.minimum + adjustment,
        band.midpoint + adjustment,
        band.maximum + adjustment,
    )
    final = tuple(min(value, rules.pal.final_maximum) for value in uncapped)
    capped = final != uncapped
    if sport_is_qualifying:
        sport_text = (
            "Der Basis-PAL bildet die gewählte Alltagstätigkeit ohne die protokollierten "
            f"Sporteinheiten ab. Nach der dokumentierten Regel werden {adjustment} PAL addiert."
        )
    else:
        sport_text = (
            "Der Basis-PAL bildet die Alltagstätigkeit ab. Das protokollierte Sportmuster "
            "erfüllt die hinterlegte DGE-basierte +0,3-Regel nicht; es wird kein erfundener "
            "Teilaufschlag verwendet."
        )
    cap_text = (
        " Die Obergrenze von 2,4 wurde sichtbar auf den berechneten Bereich angewendet."
        if capped
        else ""
    )
    return PalCalculation(
        base_minimum=band.minimum,
        base_midpoint=band.midpoint,
        base_maximum=band.maximum,
        sport_adjustment=adjustment,
        final_minimum=final[0],
        final_midpoint=final[1],
        final_maximum=final[2],
        manual_override=None,
        total_weekly_exercise_minutes=total_minutes,
        qualifying_sessions=qualifying_sessions,
        sport_was_added=sport_is_qualifying,
        final_range_was_capped=capped,
        method_id="dge_pal_band_plus_documented_sport_adjustment",
        explanation_de=f"{band.description_de} {sport_text}{cap_text}",
    )
