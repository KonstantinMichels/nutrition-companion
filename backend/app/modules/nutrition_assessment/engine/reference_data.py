"""Typed scientific-reference repository backed by versioned JSON seed data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from app.seed.loader import load_reference_values_document

from .input_models import PhysiologicalCategory
from .numeric import as_decimal


@dataclass(frozen=True, slots=True)
class ReferenceSetMetadata:
    identifier: str
    version: str
    source_organization: str
    edition: str
    publication_date: str | None
    effective_date: str
    verified_on: str
    is_complete: bool
    completeness_note_de: str


@dataclass(frozen=True, slots=True)
class NutrientDefinition:
    code: str
    display_name_de: str
    unit: str


@dataclass(frozen=True, slots=True)
class MicronutrientReferenceValue:
    nutrient_code: str
    age_min_years: int
    age_max_years_exclusive: int | None
    physiological_category: PhysiologicalCategory | None
    pregnancy_state: str
    breastfeeding_state: str
    value: Decimal | None
    lower_value: Decimal | None
    upper_value: Decimal | None
    unit: str
    reference_value_category: str
    source_identifier: str
    source_note: str

    def matches(
        self,
        *,
        age_years: int,
        physiological_category: PhysiologicalCategory,
        pregnant: bool,
        breastfeeding: bool,
    ) -> bool:
        if age_years < self.age_min_years:
            return False
        if self.age_max_years_exclusive is not None and age_years >= self.age_max_years_exclusive:
            return False
        if self.physiological_category not in {None, physiological_category}:
            return False
        expected_pregnancy = "pregnant" if pregnant else "not_pregnant"
        expected_breastfeeding = "breastfeeding" if breastfeeding else "not_breastfeeding"
        return (
            self.pregnancy_state == expected_pregnancy
            and self.breastfeeding_state == expected_breastfeeding
        )


@dataclass(frozen=True, slots=True)
class HydrationReferenceValue:
    age_min_years: int
    age_max_years_exclusive: int | None
    beverages_ml: Decimal
    food_ml: Decimal
    oxidation_ml: Decimal
    total_water_ml: Decimal
    source_identifier: str

    def matches(self, age_years: int) -> bool:
        return age_years >= self.age_min_years and (
            self.age_max_years_exclusive is None or age_years < self.age_max_years_exclusive
        )


@dataclass(frozen=True, slots=True)
class ReferenceLookup:
    nutrient: NutrientDefinition
    value: MicronutrientReferenceValue | None
    unavailable_reason_de: str | None

    @property
    def available(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class ReferenceDataRepository:
    metadata: ReferenceSetMetadata
    sources: Mapping[str, Mapping[str, Any]]
    nutrient_catalog: tuple[NutrientDefinition, ...]
    micronutrient_values: tuple[MicronutrientReferenceValue, ...]
    hydration_values: tuple[HydrationReferenceValue, ...]

    def source_metadata(self, identifier: str) -> dict[str, Any]:
        try:
            source = dict(self.sources[identifier])
        except KeyError as exc:
            raise KeyError(f"unknown scientific source {identifier}") from exc
        return {
            "reference_set_identifier": self.metadata.identifier,
            "reference_set_version": self.metadata.version,
            "scientific_reference_identifier": identifier,
            **source,
        }

    def hydration_for_age(self, age_years: int) -> HydrationReferenceValue | None:
        matches = [item for item in self.hydration_values if item.matches(age_years)]
        if len(matches) > 1:
            raise ValueError(f"overlapping hydration references for age {age_years}")
        return matches[0] if matches else None

    def lookup_micronutrient(
        self,
        nutrient_code: str,
        *,
        age_years: int,
        physiological_category: PhysiologicalCategory,
        pregnant: bool = False,
        breastfeeding: bool = False,
    ) -> ReferenceLookup:
        nutrient = next(
            (item for item in self.nutrient_catalog if item.code == nutrient_code), None
        )
        if nutrient is None:
            raise KeyError(f"unknown micronutrient code {nutrient_code}")
        matches = [
            item
            for item in self.micronutrient_values
            if item.nutrient_code == nutrient_code
            and item.matches(
                age_years=age_years,
                physiological_category=physiological_category,
                pregnant=pregnant,
                breastfeeding=breastfeeding,
            )
        ]
        # An exact category row is more specific than a category-independent row.
        matches.sort(key=lambda item: item.physiological_category is None)
        if len(matches) > 1 and (
            matches[0].physiological_category == matches[1].physiological_category
        ):
            raise ValueError(
                f"overlapping micronutrient references for {nutrient_code}, age {age_years}"
            )
        if matches:
            return ReferenceLookup(nutrient=nutrient, value=matches[0], unavailable_reason_de=None)
        if pregnant or breastfeeding:
            reason = (
                "Für Schwangerschaft oder Stillzeit ist im automatisch unterstützten MVP "
                "kein verifizierter Zielwert hinterlegt."
            )
        elif any(item.nutrient_code == nutrient_code for item in self.micronutrient_values):
            reason = (
                "Für diese Alters- und Referenzkategorie ist im verifizierten MVP-Teildatensatz "
                "noch kein Wert verfügbar."
            )
        else:
            reason = (
                "Dieser Zielwert wurde in der Ausführungsumgebung nicht aus einer offiziellen "
                "Primärquelle verifiziert und wird deshalb nicht angezeigt."
            )
        return ReferenceLookup(nutrient=nutrient, value=None, unavailable_reason_de=reason)

    def lookup_all_micronutrients(
        self,
        *,
        age_years: int,
        physiological_category: PhysiologicalCategory,
        pregnant: bool = False,
        breastfeeding: bool = False,
    ) -> tuple[ReferenceLookup, ...]:
        return tuple(
            self.lookup_micronutrient(
                nutrient.code,
                age_years=age_years,
                physiological_category=physiological_category,
                pregnant=pregnant,
                breastfeeding=breastfeeding,
            )
            for nutrient in self.nutrient_catalog
        )


def load_reference_data(
    document: Mapping[str, Any] | None = None,
) -> ReferenceDataRepository:
    raw = dict(document or load_reference_values_document())
    metadata_raw = _mapping(raw, "reference_set")
    sources_raw = _mapping(raw, "sources")
    metadata = ReferenceSetMetadata(
        identifier=str(metadata_raw["identifier"]),
        version=str(metadata_raw["version"]),
        source_organization=str(metadata_raw["source_organization"]),
        edition=str(metadata_raw["edition"]),
        publication_date=_optional_string(metadata_raw.get("publication_date")),
        effective_date=str(metadata_raw["effective_date"]),
        verified_on=str(metadata_raw["verified_on"]),
        is_complete=bool(metadata_raw["is_complete"]),
        completeness_note_de=str(metadata_raw["completeness_note_de"]),
    )
    sources: dict[str, Mapping[str, Any]] = {
        str(identifier): MappingProxyType(dict(_ensure_mapping(value, str(identifier))))
        for identifier, value in sources_raw.items()
    }

    catalog = tuple(
        NutrientDefinition(
            code=str(item["code"]),
            display_name_de=str(item["display_name_de"]),
            unit=str(item["unit"]),
        )
        for item in _list_of_mappings(raw, "nutrient_catalog")
    )
    if len({item.code for item in catalog}) != len(catalog):
        raise ValueError("nutrient catalog contains duplicate codes")

    values: list[MicronutrientReferenceValue] = []
    for item in _list_of_mappings(raw, "micronutrient_values"):
        category_raw = item.get("physiological_category")
        value = MicronutrientReferenceValue(
            nutrient_code=str(item["nutrient_code"]),
            age_min_years=int(item["age_min_years"]),
            age_max_years_exclusive=(
                None
                if item.get("age_max_years_exclusive") is None
                else int(item["age_max_years_exclusive"])
            ),
            physiological_category=(
                None if category_raw is None else PhysiologicalCategory(str(category_raw))
            ),
            pregnancy_state=str(item.get("pregnancy_state", "not_pregnant")),
            breastfeeding_state=str(item.get("breastfeeding_state", "not_breastfeeding")),
            value=_optional_decimal(item.get("value")),
            lower_value=_optional_decimal(item.get("lower_value")),
            upper_value=_optional_decimal(item.get("upper_value")),
            unit=str(item["unit"]),
            reference_value_category=str(item["reference_value_category"]),
            source_identifier=str(item["source_identifier"]),
            source_note=str(item.get("source_note", "")),
        )
        if value.nutrient_code not in {nutrient.code for nutrient in catalog}:
            raise ValueError(f"reference value has unknown code {value.nutrient_code}")
        if value.source_identifier not in sources:
            raise ValueError(f"reference value has unknown source {value.source_identifier}")
        if value.value is None and value.lower_value is None and value.upper_value is None:
            raise ValueError(f"reference value {value.nutrient_code} has no numeric value")
        values.append(value)

    hydration = tuple(
        HydrationReferenceValue(
            age_min_years=int(item["age_min_years"]),
            age_max_years_exclusive=(
                None
                if item.get("age_max_years_exclusive") is None
                else int(item["age_max_years_exclusive"])
            ),
            beverages_ml=as_decimal(item["beverages_ml"]),
            food_ml=as_decimal(item["food_ml"]),
            oxidation_ml=as_decimal(item["oxidation_ml"]),
            total_water_ml=as_decimal(item["total_water_ml"]),
            source_identifier=str(item["source_identifier"]),
        )
        for item in _list_of_mappings(raw, "hydration_values")
    )
    for hydration_item in hydration:
        if (
            hydration_item.beverages_ml + hydration_item.food_ml + hydration_item.oxidation_ml
            != hydration_item.total_water_ml
        ):
            raise ValueError(
                f"hydration components do not sum for age {hydration_item.age_min_years}"
            )
        if hydration_item.source_identifier not in sources:
            raise ValueError(f"hydration row has unknown source {hydration_item.source_identifier}")

    return ReferenceDataRepository(
        metadata=metadata,
        sources=MappingProxyType(sources),
        nutrient_catalog=catalog,
        micronutrient_values=tuple(values),
        hydration_values=hydration,
    )


def _mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    return _ensure_mapping(parent[key], key)


def _ensure_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _list_of_mappings(parent: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = parent[key]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{key} must be a list of objects")
    return value


def _optional_decimal(value: Any) -> Decimal | None:
    return None if value is None else as_decimal(value)


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value)
