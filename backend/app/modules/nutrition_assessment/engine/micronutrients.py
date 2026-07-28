"""Generic micronutrient lookup results, including explicit unavailability."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .input_models import PhysiologicalCategory
from .reference_data import ReferenceDataRepository


@dataclass(frozen=True, slots=True)
class MicronutrientTarget:
    nutrient_code: str
    display_name_de: str
    available: bool
    value: Decimal | None
    lower_value: Decimal | None
    upper_value: Decimal | None
    unit: str
    reference_value_category: str | None
    source_identifier: str | None
    source_metadata: Mapping[str, Any]
    source_note: str
    unavailable_reason_de: str | None


def lookup_micronutrient_targets(
    references: ReferenceDataRepository,
    *,
    age_years: int,
    physiological_category: PhysiologicalCategory,
    pregnant: bool = False,
    breastfeeding: bool = False,
) -> tuple[MicronutrientTarget, ...]:
    targets: list[MicronutrientTarget] = []
    for lookup in references.lookup_all_micronutrients(
        age_years=age_years,
        physiological_category=physiological_category,
        pregnant=pregnant,
        breastfeeding=breastfeeding,
    ):
        value = lookup.value
        if value is None:
            targets.append(
                MicronutrientTarget(
                    nutrient_code=lookup.nutrient.code,
                    display_name_de=lookup.nutrient.display_name_de,
                    available=False,
                    value=None,
                    lower_value=None,
                    upper_value=None,
                    unit=lookup.nutrient.unit,
                    reference_value_category=None,
                    source_identifier=None,
                    source_metadata={
                        "reference_set_identifier": references.metadata.identifier,
                        "reference_set_version": references.metadata.version,
                        "scientific_reference_identifier": None,
                        "reference_kind": "unavailable_not_in_verified_subset",
                        "reference_set_is_complete": references.metadata.is_complete,
                    },
                    source_note="",
                    unavailable_reason_de=lookup.unavailable_reason_de,
                )
            )
            continue
        targets.append(
            MicronutrientTarget(
                nutrient_code=lookup.nutrient.code,
                display_name_de=lookup.nutrient.display_name_de,
                available=True,
                value=value.value,
                lower_value=value.lower_value,
                upper_value=value.upper_value,
                unit=value.unit,
                reference_value_category=value.reference_value_category,
                source_identifier=value.source_identifier,
                source_metadata={
                    **references.source_metadata(value.source_identifier),
                    "reference_value_category": value.reference_value_category,
                    "age_min_years": value.age_min_years,
                    "age_max_years_exclusive": value.age_max_years_exclusive,
                    "physiological_category": (
                        value.physiological_category.value if value.physiological_category else None
                    ),
                    "pregnancy_state": value.pregnancy_state,
                    "breastfeeding_state": value.breastfeeding_state,
                    "source_note": value.source_note,
                },
                source_note=value.source_note,
                unavailable_reason_de=None,
            )
        )
    return tuple(targets)
