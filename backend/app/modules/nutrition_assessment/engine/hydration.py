"""Age-banded DGE baseline hydration reference lookup."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .reference_data import ReferenceDataRepository


@dataclass(frozen=True, slots=True)
class HydrationCalculation:
    available: bool
    total_water_ml: Decimal | None
    beverages_ml: Decimal | None
    food_ml: Decimal | None
    oxidation_water_ml: Decimal | None
    source_identifier: str | None
    method_id: str
    explanation_de: str


def calculate_hydration(
    age_years: int, references: ReferenceDataRepository
) -> HydrationCalculation:
    reference = references.hydration_for_age(age_years)
    if reference is None:
        return HydrationCalculation(
            available=False,
            total_water_ml=None,
            beverages_ml=None,
            food_ml=None,
            oxidation_water_ml=None,
            source_identifier=None,
            method_id="hydration_reference_unavailable",
            explanation_de=(
                "Für diese Altersgruppe ist im verifizierten MVP-Datensatz kein "
                "Hydrations-Richtwert verfügbar."
            ),
        )
    return HydrationCalculation(
        available=True,
        total_water_ml=reference.total_water_ml,
        beverages_ml=reference.beverages_ml,
        food_ml=reference.food_ml,
        oxidation_water_ml=reference.oxidation_ml,
        source_identifier=reference.source_identifier,
        method_id="dge_age_banded_baseline_water_reference",
        explanation_de=(
            "Der altersbezogene DGE-Richtwert teilt die Gesamtwasserzufuhr in Getränke, Wasser "
            "aus fester Nahrung und Oxidationswasser auf."
        ),
    )
