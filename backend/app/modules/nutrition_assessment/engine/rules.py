"""Typed application-rule configuration.

These values are product decisions and are kept separate from scientific
reference data.  No calculation module embeds its own copy of them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from app.seed.loader import load_application_rules_document

from .input_models import ActivityCategory, GoalIntensity, GoalType
from .numeric import as_decimal


@dataclass(frozen=True, slots=True)
class PalBand:
    minimum: Decimal
    midpoint: Decimal
    maximum: Decimal
    description_de: str


@dataclass(frozen=True, slots=True)
class PalRules:
    source_identifier: str
    categories: Mapping[ActivityCategory, PalBand]
    sport_rule_identifier: str
    minimum_qualifying_sessions: Decimal
    minimum_minutes_per_session: Decimal
    qualifying_intensities: tuple[str, ...]
    sport_adjustment: Decimal
    final_maximum: Decimal
    base_categories_include_logged_sport: bool
    manual_override_includes_all_activity: bool
    manual_override_minimum: Decimal
    manual_override_maximum: Decimal
    sport_note_de: str


@dataclass(frozen=True, slots=True)
class ProteinRules:
    general_adult_g_per_kg: Decimal
    age_18_category_a_g_per_kg: Decimal
    age_18_category_b_g_per_kg: Decimal
    age_65_g_per_kg: Decimal
    athletic_threshold_hours_exclusive: Decimal
    athletic_minimum_g_per_kg: Decimal
    athletic_upper_g_per_kg: Decimal
    selections_g_per_kg: Mapping[str, Decimal]
    selection_note_de: str


@dataclass(frozen=True, slots=True)
class MacronutrientRules:
    fat_energy_percent: Decimal
    saturated_fat_max_energy_percent: Decimal
    carbohydrate_guidance_energy_percent_exclusive: Decimal
    protein_kcal_per_g: Decimal
    carbohydrate_kcal_per_g: Decimal
    fat_kcal_per_g: Decimal


@dataclass(frozen=True, slots=True)
class FiberRules:
    absolute_minimum_g_per_day: Decimal
    energy_relative_g_per_1000_kcal: Decimal


@dataclass(frozen=True, slots=True)
class EnergySafetyRules:
    maximum_deficit_percent: Decimal
    apply_ree_floor: bool
    aggressive_requested_weekly_change_kg: Decimal


@dataclass(frozen=True, slots=True)
class ValidationRules:
    age_minimum: int
    age_maximum: int
    height_cm_minimum_exclusive: Decimal
    height_cm_maximum: Decimal
    weight_kg_minimum_exclusive: Decimal
    weight_kg_maximum: Decimal
    body_fat_percent_minimum: Decimal
    body_fat_percent_maximum: Decimal
    circumference_cm_minimum: Decimal
    circumference_cm_maximum: Decimal
    measured_ree_minimum: Decimal
    measured_ree_maximum: Decimal
    sport_sessions_maximum: Decimal
    sport_minutes_per_session_maximum: Decimal
    target_weight_kg_minimum_exclusive: Decimal
    target_weight_kg_maximum: Decimal
    requested_weekly_rate_kg_maximum: Decimal


@dataclass(frozen=True, slots=True)
class ApplicationRules:
    identifier: str
    version: str
    name: str
    effective_date: str
    engine_version: str
    classification: str
    pal: PalRules
    goal_adjustments_percent: Mapping[str, Decimal]
    energy_safety: EnergySafetyRules
    protein: ProteinRules
    macronutrients: MacronutrientRules
    fiber: FiberRules
    validation: ValidationRules
    presentation_decimal_places: Mapping[str, int]

    def goal_adjustment_percent(
        self, goal_type: GoalType, intensity: GoalIntensity | None
    ) -> Decimal:
        key = goal_type.value
        if intensity is not None:
            key = f"{key}.{intensity.value}"
        try:
            return self.goal_adjustments_percent[key]
        except KeyError as exc:
            raise ValueError(f"no configured goal adjustment for {key}") from exc

    def display_places(self, kind: str) -> int:
        try:
            return self.presentation_decimal_places[kind]
        except KeyError as exc:
            raise ValueError(f"no display-rounding rule for {kind}") from exc


def load_application_rules(document: Mapping[str, Any] | None = None) -> ApplicationRules:
    raw = dict(document or load_application_rules_document())
    metadata = _mapping(raw, "rule_set")
    pal_raw = _mapping(raw, "pal")
    category_raw = _mapping(pal_raw, "categories")
    categories: dict[ActivityCategory, PalBand] = {}
    for key, item in category_raw.items():
        category = ActivityCategory(key)
        values = _ensure_mapping(item, f"pal.categories.{key}")
        band = PalBand(
            minimum=as_decimal(values["minimum"]),
            midpoint=as_decimal(values["midpoint"]),
            maximum=as_decimal(values["maximum"]),
            description_de=str(values["description_de"]),
        )
        if not band.minimum <= band.midpoint <= band.maximum:
            raise ValueError(f"invalid PAL band for {key}")
        categories[category] = band

    sport = _mapping(pal_raw, "sport_adjustment")
    pal = PalRules(
        source_identifier=str(pal_raw["source_identifier"]),
        categories=MappingProxyType(categories),
        sport_rule_identifier=str(sport["rule_identifier"]),
        minimum_qualifying_sessions=as_decimal(sport["minimum_qualifying_sessions_per_week"]),
        minimum_minutes_per_session=as_decimal(sport["minimum_minutes_per_qualifying_session"]),
        qualifying_intensities=tuple(str(value) for value in sport["qualifying_intensities"]),
        sport_adjustment=as_decimal(sport["adjustment"]),
        final_maximum=as_decimal(sport["final_pal_maximum"]),
        base_categories_include_logged_sport=bool(sport["base_categories_include_logged_sport"]),
        manual_override_includes_all_activity=bool(sport["manual_override_includes_all_activity"]),
        manual_override_minimum=as_decimal(pal_raw["manual_override_minimum"]),
        manual_override_maximum=as_decimal(pal_raw["manual_override_maximum"]),
        sport_note_de=str(sport["note_de"]),
    )

    goal_raw = _mapping(raw, "energy_goal_adjustments_percent")
    goal_adjustments: dict[str, Decimal] = {}
    for goal_key, values_raw in goal_raw.items():
        values = _ensure_mapping(values_raw, f"energy_goal_adjustments_percent.{goal_key}")
        for intensity_key, value in values.items():
            key = goal_key if intensity_key == "default" else f"{goal_key}.{intensity_key}"
            goal_adjustments[key] = as_decimal(value)

    safety_raw = _mapping(raw, "energy_safety")
    protein_raw = _mapping(raw, "protein")
    protein_selections = {
        str(key): as_decimal(value)
        for key, value in _mapping(protein_raw, "selection_g_per_kg").items()
    }
    macro_raw = _mapping(raw, "macronutrients")
    fiber_raw = _mapping(raw, "fiber")
    validation_raw = _mapping(raw, "validation")
    display_raw = _mapping(raw, "presentation_decimal_places")

    return ApplicationRules(
        identifier=str(metadata["identifier"]),
        version=str(metadata["version"]),
        name=str(metadata["name"]),
        effective_date=str(metadata["effective_date"]),
        engine_version=str(metadata["engine_version"]),
        classification=str(metadata["classification"]),
        pal=pal,
        goal_adjustments_percent=MappingProxyType(goal_adjustments),
        energy_safety=EnergySafetyRules(
            maximum_deficit_percent=as_decimal(safety_raw["maximum_deficit_percent"]),
            apply_ree_floor=bool(safety_raw["apply_ree_floor"]),
            aggressive_requested_weekly_change_kg=as_decimal(
                safety_raw["aggressive_requested_weekly_change_kg"]
            ),
        ),
        protein=ProteinRules(
            general_adult_g_per_kg=as_decimal(protein_raw["general_adult_19_to_under_65_g_per_kg"]),
            age_18_category_a_g_per_kg=as_decimal(protein_raw["age_18_category_a_g_per_kg"]),
            age_18_category_b_g_per_kg=as_decimal(protein_raw["age_18_category_b_g_per_kg"]),
            age_65_g_per_kg=as_decimal(protein_raw["age_65_g_per_kg"]),
            athletic_threshold_hours_exclusive=as_decimal(
                protein_raw["athletic_threshold_hours_exclusive"]
            ),
            athletic_minimum_g_per_kg=as_decimal(protein_raw["athletic_minimum_g_per_kg"]),
            athletic_upper_g_per_kg=as_decimal(protein_raw["athletic_upper_g_per_kg"]),
            selections_g_per_kg=MappingProxyType(protein_selections),
            selection_note_de=str(protein_raw["selection_note_de"]),
        ),
        macronutrients=MacronutrientRules(
            fat_energy_percent=as_decimal(macro_raw["fat_energy_percent"]),
            saturated_fat_max_energy_percent=as_decimal(
                macro_raw["saturated_fat_max_energy_percent"]
            ),
            carbohydrate_guidance_energy_percent_exclusive=as_decimal(
                macro_raw["carbohydrate_guidance_energy_percent_exclusive"]
            ),
            protein_kcal_per_g=as_decimal(macro_raw["protein_kcal_per_g"]),
            carbohydrate_kcal_per_g=as_decimal(macro_raw["carbohydrate_kcal_per_g"]),
            fat_kcal_per_g=as_decimal(macro_raw["fat_kcal_per_g"]),
        ),
        fiber=FiberRules(
            absolute_minimum_g_per_day=as_decimal(fiber_raw["absolute_minimum_g_per_day"]),
            energy_relative_g_per_1000_kcal=as_decimal(
                fiber_raw["energy_relative_g_per_1000_kcal"]
            ),
        ),
        validation=ValidationRules(
            age_minimum=int(validation_raw["age_minimum"]),
            age_maximum=int(validation_raw["age_maximum"]),
            height_cm_minimum_exclusive=as_decimal(validation_raw["height_cm_minimum_exclusive"]),
            height_cm_maximum=as_decimal(validation_raw["height_cm_maximum"]),
            weight_kg_minimum_exclusive=as_decimal(validation_raw["weight_kg_minimum_exclusive"]),
            weight_kg_maximum=as_decimal(validation_raw["weight_kg_maximum"]),
            body_fat_percent_minimum=as_decimal(validation_raw["body_fat_percent_minimum"]),
            body_fat_percent_maximum=as_decimal(validation_raw["body_fat_percent_maximum"]),
            circumference_cm_minimum=as_decimal(validation_raw["circumference_cm_minimum"]),
            circumference_cm_maximum=as_decimal(validation_raw["circumference_cm_maximum"]),
            measured_ree_minimum=as_decimal(validation_raw["measured_ree_minimum"]),
            measured_ree_maximum=as_decimal(validation_raw["measured_ree_maximum"]),
            sport_sessions_maximum=as_decimal(validation_raw["sport_sessions_maximum"]),
            sport_minutes_per_session_maximum=as_decimal(
                validation_raw["sport_minutes_per_session_maximum"]
            ),
            target_weight_kg_minimum_exclusive=as_decimal(
                validation_raw["target_weight_kg_minimum_exclusive"]
            ),
            target_weight_kg_maximum=as_decimal(validation_raw["target_weight_kg_maximum"]),
            requested_weekly_rate_kg_maximum=as_decimal(
                validation_raw["requested_weekly_rate_kg_maximum"]
            ),
        ),
        presentation_decimal_places=MappingProxyType(
            {str(key): int(value) for key, value in display_raw.items()}
        ),
    )


def _mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    return _ensure_mapping(parent[key], key)


def _ensure_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value
