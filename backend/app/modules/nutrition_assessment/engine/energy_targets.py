"""Maintenance and conservative goal-adjusted energy calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .activity import PalCalculation
from .input_models import GoalIntensity, GoalType
from .numeric import DecimalLike, as_decimal
from .rules import ApplicationRules


@dataclass(frozen=True, slots=True)
class EnergyRange:
    lower: Decimal
    midpoint: Decimal
    upper: Decimal

    def __post_init__(self) -> None:
        if not self.lower <= self.midpoint <= self.upper:
            raise ValueError("energy range must be ordered")


def calculate_tdee(resting_energy_kcal: DecimalLike, pal: PalCalculation) -> EnergyRange:
    resting = as_decimal(resting_energy_kcal, field="resting_energy_kcal")
    if resting <= 0:
        raise ValueError("resting energy must be positive")
    return EnergyRange(
        lower=resting * pal.final_minimum,
        midpoint=resting * pal.final_midpoint,
        upper=resting * pal.final_maximum,
    )


@dataclass(frozen=True, slots=True)
class GoalEnergyCalculation:
    available: bool
    energy_range: EnergyRange | None
    configured_adjustment_percent: Decimal
    applied_adjustment_percent: Decimal
    deficit_was_capped: bool
    ree_floor_was_applied: bool
    aggressive_requested_change: bool
    requested_weekly_rate_was_not_used: bool
    method_id: str
    explanation_de: str


def calculate_goal_energy(
    *,
    maintenance: EnergyRange,
    resting_energy_kcal: DecimalLike,
    goal_type: GoalType | str,
    intensity: GoalIntensity | str | None,
    rules: ApplicationRules,
    supported_scope: bool = True,
    requested_adjustment_percent: DecimalLike | None = None,
    requested_weekly_rate_kg: DecimalLike | None = None,
) -> GoalEnergyCalculation:
    goal = GoalType(goal_type)
    parsed_intensity = GoalIntensity(intensity) if intensity else None
    configured = (
        rules.goal_adjustment_percent(goal, parsed_intensity)
        if requested_adjustment_percent is None
        else as_decimal(requested_adjustment_percent, field="requested_adjustment_percent")
    )
    deficit_floor = -rules.energy_safety.maximum_deficit_percent
    applied = max(configured, deficit_floor)
    capped = applied != configured
    weekly_rate = (
        None
        if requested_weekly_rate_kg is None
        else as_decimal(requested_weekly_rate_kg, field="requested_weekly_rate_kg")
    )
    aggressive = weekly_rate is not None and (
        weekly_rate > rules.energy_safety.aggressive_requested_weekly_change_kg
    )
    rate_not_used = weekly_rate is not None

    if not supported_scope:
        return GoalEnergyCalculation(
            available=False,
            energy_range=None,
            configured_adjustment_percent=configured,
            applied_adjustment_percent=applied,
            deficit_was_capped=capped,
            ree_floor_was_applied=False,
            aggressive_requested_change=aggressive,
            requested_weekly_rate_was_not_used=rate_not_used,
            method_id="goal_energy_withheld_unsupported_scope",
            explanation_de=(
                "Für eine Situation außerhalb des unterstützten MVP-Bereichs wird kein normaler "
                "zielangepasster Energiebereich berechnet."
            ),
        )

    factor = Decimal(1) + applied / Decimal(100)
    raw = EnergyRange(
        lower=maintenance.lower * factor,
        midpoint=maintenance.midpoint * factor,
        upper=maintenance.upper * factor,
    )
    resting = as_decimal(resting_energy_kcal, field="resting_energy_kcal")
    below_ree = raw.lower < resting or raw.midpoint < resting or raw.upper < resting
    if below_ree and rules.energy_safety.apply_ree_floor:
        adjusted = EnergyRange(
            lower=max(raw.lower, resting),
            midpoint=max(raw.midpoint, resting),
            upper=max(raw.upper, resting),
        )
    else:
        adjusted = raw
    source = "manuell angefragte" if requested_adjustment_percent is not None else "hinterlegte"
    explanation = (
        f"Der Erhaltungsbereich wurde mit der {source} Anpassung von {applied} % multipliziert."
    )
    if capped:
        explanation += " Das angefragte Defizit wurde sichtbar auf maximal 20 % begrenzt."
    if below_ree and rules.energy_safety.apply_ree_floor:
        explanation += (
            " Mindestens ein Wert hätte unter dem Ruheenergieverbrauch gelegen und wurde "
            "deshalb sichtbar auf den Ruheenergieverbrauch angehoben."
        )
    if rate_not_used:
        explanation += (
            " Die gewünschte wöchentliche Gewichtsänderung wird dokumentiert, aber nicht in eine "
            "garantierte Energiewirkung oder ein Zieldatum umgerechnet."
        )
    return GoalEnergyCalculation(
        available=True,
        energy_range=adjusted,
        configured_adjustment_percent=configured,
        applied_adjustment_percent=applied,
        deficit_was_capped=capped,
        ree_floor_was_applied=below_ree and rules.energy_safety.apply_ree_floor,
        aggressive_requested_change=aggressive,
        requested_weekly_rate_was_not_used=rate_not_used,
        method_id="maintenance_range_times_goal_adjustment_with_ree_floor",
        explanation_de=explanation,
    )
