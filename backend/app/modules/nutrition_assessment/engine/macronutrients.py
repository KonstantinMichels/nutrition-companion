"""Protein selection and internally consistent macro-energy distribution."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .energy_targets import EnergyRange
from .input_models import AssessmentInput, GoalType, PhysiologicalCategory, SportType
from .rules import ApplicationRules


@dataclass(frozen=True, slots=True)
class ProteinCalculation:
    available: bool
    minimum_g_per_kg: Decimal | None
    default_g_per_kg: Decimal | None
    upper_g_per_kg: Decimal | None
    minimum_grams_per_day: Decimal | None
    default_grams_per_day: Decimal | None
    upper_grams_per_day: Decimal | None
    weekly_training_hours: Decimal
    athletic_range_eligible: bool
    athletic_range_suppressed_for_safety: bool
    selection_rule_id: str
    scientific_reference_identifier: str | None
    explanation_de: str


def calculate_protein(
    data: AssessmentInput,
    rules: ApplicationRules,
    *,
    supported_scope: bool,
) -> ProteinCalculation:
    hours = data.total_weekly_exercise_minutes / Decimal(60)
    if not 18 <= data.age_years <= 65:
        return ProteinCalculation(
            available=False,
            minimum_g_per_kg=None,
            default_g_per_kg=None,
            upper_g_per_kg=None,
            minimum_grams_per_day=None,
            default_grams_per_day=None,
            upper_grams_per_day=None,
            weekly_training_hours=hours,
            athletic_range_eligible=False,
            athletic_range_suppressed_for_safety=False,
            selection_rule_id="protein_unavailable_unsupported_age",
            scientific_reference_identifier=None,
            explanation_de=(
                "Für dieses Alter wird im automatisch unterstützten MVP kein Proteinziel erzeugt."
            ),
        )

    base = _base_protein_g_per_kg(data, rules)
    athletic_eligible = hours > rules.protein.athletic_threshold_hours_exclusive
    suppressed = athletic_eligible and not supported_scope
    if not athletic_eligible or suppressed:
        if suppressed:
            explanation = (
                "Der sportliche Zielbereich wurde wegen einer Situation außerhalb des "
                "unterstützten MVP-Scope nicht erzeugt. Angezeigt wird nur der allgemeine "
                "altersbezogene Referenzwert, nicht eine medizinische Empfehlung."
            )
            rule_id = "athletic_protein_suppressed_use_general_reference"
        else:
            explanation = (
                "Bei höchstens fünf Trainingsstunden pro Woche wird Protein nicht allein wegen "
                "des Sports erhöht; es gilt der allgemeine altersbezogene Referenzwert."
            )
            rule_id = "general_protein_reference_no_athletic_increase"
        grams = base * data.weight_kg
        return ProteinCalculation(
            available=True,
            minimum_g_per_kg=base,
            default_g_per_kg=base,
            upper_g_per_kg=None,
            minimum_grams_per_day=grams,
            default_grams_per_day=grams,
            upper_grams_per_day=None,
            weekly_training_hours=hours,
            athletic_range_eligible=athletic_eligible,
            athletic_range_suppressed_for_safety=suppressed,
            selection_rule_id=rule_id,
            scientific_reference_identifier="dge_protein_2017",
            explanation_de=explanation,
        )

    selection_key, focus = _athletic_selection_key(data)
    selected = rules.protein.selections_g_per_kg[selection_key]
    minimum = rules.protein.athletic_minimum_g_per_kg
    upper = rules.protein.athletic_upper_g_per_kg
    return ProteinCalculation(
        available=True,
        minimum_g_per_kg=minimum,
        default_g_per_kg=selected,
        upper_g_per_kg=upper,
        minimum_grams_per_day=minimum * data.weight_kg,
        default_grams_per_day=selected * data.weight_kg,
        upper_grams_per_day=upper * data.weight_kg,
        weekly_training_hours=hours,
        athletic_range_eligible=True,
        athletic_range_suppressed_for_safety=False,
        selection_rule_id=f"athletic_protein_{selection_key}",
        scientific_reference_identifier="dge_sport_protein_2020",
        explanation_de=(
            "Bei mehr als fünf Trainingsstunden pro Woche gilt der DGE-basierte Bereich von "
            f"{minimum} bis {upper} g/kg/Tag. Für den ermittelten Trainingsfokus '{focus}' und "
            f"das Ziel '{data.goal.goal_type.value}' wählt die MVP-Anwendungsregel {selected} "
            "g/kg/Tag; dies ist keine medizinische Hochprotein-Empfehlung."
        ),
    )


def _base_protein_g_per_kg(data: AssessmentInput, rules: ApplicationRules) -> Decimal:
    if data.age_years == 18:
        return (
            rules.protein.age_18_category_a_g_per_kg
            if data.physiological_category is PhysiologicalCategory.REFERENCE_CATEGORY_A
            else rules.protein.age_18_category_b_g_per_kg
        )
    if data.age_years == 65:
        return rules.protein.age_65_g_per_kg
    return rules.protein.general_adult_g_per_kg


def _athletic_selection_key(data: AssessmentInput) -> tuple[str, str]:
    if data.goal.goal_type is GoalType.LOSE_WEIGHT:
        return "weight_loss_with_substantial_training", "weight_loss_phase"
    buckets: dict[str, Decimal] = defaultdict(Decimal)
    for sport in data.sports:
        if sport.sport_type is SportType.STRENGTH_TRAINING:
            bucket = "strength"
        elif sport.sport_type in {
            SportType.CYCLING,
            SportType.RUNNING,
            SportType.SWIMMING,
            SportType.ENDURANCE_TRAINING,
        }:
            bucket = "endurance"
        elif sport.sport_type in {SportType.TEAM_SPORT, SportType.MIXED_TRAINING}:
            bucket = "mixed"
        else:
            bucket = "other"
        buckets[bucket] += sport.weekly_minutes
    # Explicit order resolves ties deterministically.
    focus = max(("strength", "mixed", "endurance", "other"), key=lambda key: buckets[key])
    if data.goal.goal_type is GoalType.GAIN_WEIGHT or focus == "strength":
        return "strength_or_weight_gain", focus
    if data.goal.goal_type is GoalType.ATHLETIC_PERFORMANCE:
        return "athletic_performance", focus
    if focus == "mixed":
        return "mixed_or_team", focus
    if focus == "endurance":
        return "endurance_maintenance", focus
    return "other_athletic", focus


@dataclass(frozen=True, slots=True)
class MacronutrientCalculation:
    energy: EnergyRange
    protein_grams: Decimal
    protein_energy_percent: Decimal
    fat_grams: Decimal
    fat_grams_lower: Decimal
    fat_grams_upper: Decimal
    fat_energy_percent: Decimal
    saturated_fat_max_grams: Decimal
    saturated_fat_max_energy_percent: Decimal
    carbohydrate_grams: Decimal
    carbohydrate_grams_lower: Decimal
    carbohydrate_grams_upper: Decimal
    carbohydrate_energy_percent: Decimal
    macro_energy_sum_kcal: Decimal
    carbohydrate_below_standard_guidance: bool


def calculate_macronutrients(
    *,
    energy: EnergyRange,
    protein_grams: Decimal,
    rules: ApplicationRules,
) -> MacronutrientCalculation:
    macro = rules.macronutrients
    protein_energy = protein_grams * macro.protein_kcal_per_g

    def fat_for(kcal: Decimal) -> Decimal:
        return kcal * macro.fat_energy_percent / Decimal(100) / macro.fat_kcal_per_g

    def carbohydrate_for(kcal: Decimal) -> Decimal:
        fat_energy = fat_for(kcal) * macro.fat_kcal_per_g
        remaining = kcal - protein_energy - fat_energy
        if remaining < 0:
            raise ValueError("selected protein and fat leave negative carbohydrate energy")
        return remaining / macro.carbohydrate_kcal_per_g

    fat = fat_for(energy.midpoint)
    carbohydrate = carbohydrate_for(energy.midpoint)
    carbohydrate_percent = (
        carbohydrate * macro.carbohydrate_kcal_per_g / energy.midpoint * Decimal(100)
    )
    protein_percent = protein_energy / energy.midpoint * Decimal(100)
    macro_sum = (
        protein_energy + fat * macro.fat_kcal_per_g + carbohydrate * macro.carbohydrate_kcal_per_g
    )
    return MacronutrientCalculation(
        energy=energy,
        protein_grams=protein_grams,
        protein_energy_percent=protein_percent,
        fat_grams=fat,
        fat_grams_lower=fat_for(energy.lower),
        fat_grams_upper=fat_for(energy.upper),
        fat_energy_percent=macro.fat_energy_percent,
        saturated_fat_max_grams=(
            energy.midpoint
            * macro.saturated_fat_max_energy_percent
            / Decimal(100)
            / macro.fat_kcal_per_g
        ),
        saturated_fat_max_energy_percent=macro.saturated_fat_max_energy_percent,
        carbohydrate_grams=carbohydrate,
        carbohydrate_grams_lower=carbohydrate_for(energy.lower),
        carbohydrate_grams_upper=carbohydrate_for(energy.upper),
        carbohydrate_energy_percent=carbohydrate_percent,
        macro_energy_sum_kcal=macro_sum,
        carbohydrate_below_standard_guidance=(
            carbohydrate_percent <= macro.carbohydrate_guidance_energy_percent_exclusive
        ),
    )
