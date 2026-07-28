"""DGE fiber target: higher of absolute and energy-relative rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .energy_targets import EnergyRange
from .rules import ApplicationRules


@dataclass(frozen=True, slots=True)
class FiberCalculation:
    absolute_minimum_g: Decimal
    energy_relative_g: Decimal
    selected_g: Decimal
    selected_lower_g: Decimal
    selected_upper_g: Decimal
    method_id: str


def calculate_fiber(energy: EnergyRange, rules: ApplicationRules) -> FiberCalculation:
    absolute = rules.fiber.absolute_minimum_g_per_day

    def relative(kcal: Decimal) -> Decimal:
        return rules.fiber.energy_relative_g_per_1000_kcal * kcal / Decimal(1000)

    midpoint_relative = relative(energy.midpoint)
    return FiberCalculation(
        absolute_minimum_g=absolute,
        energy_relative_g=midpoint_relative,
        selected_g=max(absolute, midpoint_relative),
        selected_lower_g=max(absolute, relative(energy.lower)),
        selected_upper_g=max(absolute, relative(energy.upper)),
        method_id="higher_of_30_g_or_14_6_g_per_1000_kcal",
    )
