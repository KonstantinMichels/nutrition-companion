"""Pure orchestration of a complete, reproducible nutrition assessment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from .activity import PalCalculation, calculate_pal
from .anthropometrics import (
    calculate_bmi,
    calculate_body_composition,
    calculate_waist_to_height_ratio,
    calculate_waist_to_hip_ratio,
)
from .energy_targets import (
    EnergyRange,
    GoalEnergyCalculation,
    calculate_goal_energy,
    calculate_tdee,
)
from .fiber import calculate_fiber
from .food_groups import load_food_group_recommendations
from .hydration import calculate_hydration
from .input_models import AssessmentInput, MeasurementSource
from .macronutrients import ProteinCalculation, calculate_macronutrients, calculate_protein
from .micronutrients import MicronutrientTarget, lookup_micronutrient_targets
from .numeric import format_decimal_de
from .reference_data import ReferenceDataRepository, load_reference_data
from .resting_energy import RestingEnergyCalculation, calculate_resting_energy
from .result_models import (
    AssessmentResult,
    ConfidenceType,
    FoodGroupRecommendation,
    MetricResult,
    SafetyFlag,
    SafetySeverity,
    SupportedScopeStatus,
)
from .rules import ApplicationRules, load_application_rules
from .safety import assess_supported_scope, high_protein_kidney_flag
from .validation import validate_assessment_input


@dataclass(frozen=True, slots=True)
class NutritionEngine:
    rules: ApplicationRules
    references: ReferenceDataRepository
    food_groups: tuple[FoodGroupRecommendation, ...]

    @classmethod
    def from_seed_data(cls) -> NutritionEngine:
        return cls(
            rules=load_application_rules(),
            references=load_reference_data(),
            food_groups=load_food_group_recommendations(),
        )

    def assess(self, data: AssessmentInput, *, calculated_at: datetime) -> AssessmentResult:
        if calculated_at.tzinfo is None or calculated_at.utcoffset() is None:
            raise ValueError("calculated_at must be timezone-aware")
        validate_assessment_input(data, self.rules, calculated_at)
        scope = assess_supported_scope(data)
        supported = scope.status is SupportedScopeStatus.SUPPORTED
        metrics: list[MetricResult] = []
        safety_flags = list(scope.flags)

        self._append_anthropometric_metrics(metrics, data, calculated_at)
        resting = calculate_resting_energy(data)
        self._append_resting_metrics(metrics, data, resting, calculated_at)
        pal = calculate_pal(data, self.rules)
        metrics.append(self._pal_metric(data, pal, calculated_at))
        if pal.final_range_was_capped:
            safety_flags.append(
                SafetyFlag(
                    code="PAL_RANGE_CAPPED",
                    severity=SafetySeverity.INFO,
                    explanation_de=(
                        "Der PAL-Bereich wurde bei der dokumentierten DGE-Obergrenze 2,4 begrenzt."
                    ),
                    recommended_action_de=(
                        "Behandle den Bereich als Schätzung; bei außergewöhnlich hoher Aktivität "
                        "kann eine individuelle Messung sinnvoll sein."
                    ),
                )
            )

        maintenance = calculate_tdee(resting.selected_kcal_per_day, pal)
        metrics.append(self._maintenance_metric(resting, pal, maintenance, calculated_at))
        goal_energy = calculate_goal_energy(
            maintenance=maintenance,
            resting_energy_kcal=resting.selected_kcal_per_day,
            goal_type=data.goal.goal_type,
            intensity=data.goal.desired_intensity,
            rules=self.rules,
            supported_scope=supported,
            requested_weekly_rate_kg=data.goal.requested_weekly_rate_kg,
        )
        metrics.append(self._goal_energy_metric(goal_energy, maintenance, calculated_at))
        safety_flags.extend(self._goal_safety_flags(goal_energy))

        protein = calculate_protein(data, self.rules, supported_scope=supported)
        self._append_protein_metrics(metrics, data, protein, calculated_at)
        if data.health_screening.kidney_disease and protein.athletic_range_eligible:
            safety_flags.append(high_protein_kidney_flag())

        if goal_energy.available and goal_energy.energy_range and protein.default_grams_per_day:
            macro = calculate_macronutrients(
                energy=goal_energy.energy_range,
                protein_grams=protein.default_grams_per_day,
                rules=self.rules,
            )
            self._append_macro_metrics(metrics, macro, calculated_at)
            if macro.carbohydrate_below_standard_guidance:
                safety_flags.append(
                    SafetyFlag(
                        code="CARBOHYDRATE_SHARE_BELOW_STANDARD_GUIDANCE",
                        severity=SafetySeverity.INFO,
                        explanation_de=(
                            "Nach Abzug des ausgewählten Protein- und Fettanteils liegt der "
                            "Kohlenhydratanteil nicht über 50 Energieprozent."
                        ),
                        recommended_action_de=(
                            "Die Verteilung wird transparent angezeigt und nicht künstlich auf "
                            "einen mathematisch unvereinbaren Wert gezwungen."
                        ),
                    )
                )
            fiber = calculate_fiber(goal_energy.energy_range, self.rules)
            metrics.append(
                self._metric(
                    code="fiber.target",
                    raw=fiber.selected_g,
                    lower=fiber.selected_lower_g,
                    upper=fiber.selected_upper_g,
                    unit="g/Tag",
                    method=fiber.method_id,
                    explanation=(
                        "Aus mindestens 30 g/Tag und mindestens 14,6 g je 1.000 kcal wird "
                        "jeweils der höhere Wert angezeigt."
                    ),
                    limitations=(
                        "Dies ist ein Richtwert. Eine ausreichende Flüssigkeitszufuhr und "
                        "individuelle Verträglichkeit sind zu berücksichtigen."
                    ),
                    inputs={
                        "energy_lower_kcal": goal_energy.energy_range.lower,
                        "energy_midpoint_kcal": goal_energy.energy_range.midpoint,
                        "energy_upper_kcal": goal_energy.energy_range.upper,
                        "absolute_minimum_g": fiber.absolute_minimum_g,
                        "energy_relative_g_midpoint": fiber.energy_relative_g,
                    },
                    source=self.references.source_metadata("dge_fiber_2021"),
                    application_rule="fiber_higher_applicable_target",
                    confidence=ConfidenceType.REFERENCE_TARGET,
                    display_kind="grams",
                    calculated_at=calculated_at,
                )
            )
        else:
            self._append_unavailable_macros_and_fiber(metrics, calculated_at)

        self._append_hydration_metrics(metrics, data, calculated_at)
        micronutrients = lookup_micronutrient_targets(
            self.references,
            age_years=data.age_years,
            physiological_category=data.physiological_category,
            pregnant=data.health_screening.pregnant,
            breastfeeding=data.health_screening.breastfeeding,
        )
        self._append_micronutrient_metrics(metrics, micronutrients, data, calculated_at)

        available_codes = [target.nutrient_code for target in micronutrients if target.available]
        unavailable_codes = [
            target.nutrient_code for target in micronutrients if not target.available
        ]
        energy_summary = (
            {
                "available": True,
                "lower": str(goal_energy.energy_range.lower),
                "midpoint": str(goal_energy.energy_range.midpoint),
                "upper": str(goal_energy.energy_range.upper),
                "unit": "kcal/Tag",
            }
            if goal_energy.energy_range
            else {
                "available": False,
                "lower": None,
                "midpoint": None,
                "upper": None,
                "unit": "kcal/Tag",
            }
        )
        protein_summary = {
            "available": protein.available,
            "minimum": _optional_string(protein.minimum_grams_per_day),
            "default": _optional_string(protein.default_grams_per_day),
            "upper": _optional_string(protein.upper_grams_per_day),
            "unit": "g/Tag",
        }
        summary: dict[str, Any] = {
            "goal_type": data.goal.goal_type.value,
            "supported_scope": supported,
            "total_weekly_exercise_minutes": str(data.total_weekly_exercise_minutes),
            "energy_target": energy_summary,
            "protein_target": protein_summary,
            "micronutrients": {
                "available_codes": available_codes,
                "unavailable_codes": unavailable_codes,
                "reference_set_complete": self.references.metadata.is_complete,
            },
            "food_groups": [item.to_dict() for item in self.food_groups],
        }
        return AssessmentResult(
            supported_scope_status=scope.status,
            reference_set_identifier=self.references.metadata.identifier,
            reference_set_version=self.references.metadata.version,
            application_rule_set_identifier=self.rules.identifier,
            application_rule_set_version=self.rules.version,
            engine_version=self.rules.engine_version,
            calculated_at=calculated_at,
            input_snapshot=data.to_snapshot(),
            summary=summary,
            metrics=tuple(metrics),
            safety_flags=_deduplicate_flags(safety_flags),
            food_groups=self.food_groups,
        )

    def _append_anthropometric_metrics(
        self, metrics: list[MetricResult], data: AssessmentInput, calculated_at: datetime
    ) -> None:
        source = self.references.source_metadata("mvp_spec_anthropometrics")
        bmi = calculate_bmi(data.weight_kg, data.height_cm)
        metrics.append(
            self._metric(
                code="anthropometrics.bmi",
                raw=bmi,
                unit="kg/m²",
                method="bmi_weight_divided_by_height_squared",
                explanation=(
                    "Der BMI ergibt sich aus Körpergewicht geteilt durch Körpergröße in Metern "
                    "zum Quadrat."
                ),
                limitations=(
                    "Der BMI ist eine zusätzliche Körperkennzahl, keine Diagnose und nicht die "
                    "alleinige Grundlage der Empfehlungen."
                ),
                inputs={"weight_kg": data.weight_kg, "height_cm": data.height_cm},
                source=source,
                confidence=ConfidenceType.DERIVED,
                display_kind="bmi",
                calculated_at=calculated_at,
            )
        )
        if data.waist_circumference is not None:
            ratio = calculate_waist_to_height_ratio(data.waist_circumference.value, data.height_cm)
            metrics.append(
                self._metric(
                    code="anthropometrics.waist_to_height_ratio",
                    raw=ratio,
                    unit="Verhältnis",
                    method="waist_cm_divided_by_height_cm",
                    explanation="Taillenumfang geteilt durch Körpergröße in derselben Einheit.",
                    limitations=(
                        "Zusätzliche Körperkennzahl; daraus wird keine Erkrankung abgeleitet."
                    ),
                    inputs={
                        "waist_cm": data.waist_circumference.value,
                        "height_cm": data.height_cm,
                        "measurement_date": data.waist_circumference.measured_at,
                        "measurement_source": data.waist_circumference.source_type.value,
                    },
                    source=source,
                    confidence=ConfidenceType.DERIVED,
                    display_kind="ratio",
                    calculated_at=calculated_at,
                )
            )
        if data.waist_circumference is not None and data.hip_circumference is not None:
            ratio = calculate_waist_to_hip_ratio(
                data.waist_circumference.value, data.hip_circumference.value
            )
            metrics.append(
                self._metric(
                    code="anthropometrics.waist_to_hip_ratio",
                    raw=ratio,
                    unit="Verhältnis",
                    method="waist_cm_divided_by_hip_cm",
                    explanation="Taillenumfang geteilt durch Hüftumfang in derselben Einheit.",
                    limitations=(
                        "Zusätzliche Körperkennzahl; daraus wird keine Erkrankung abgeleitet."
                    ),
                    inputs={
                        "waist_cm": data.waist_circumference.value,
                        "hip_cm": data.hip_circumference.value,
                        "waist_measurement_date": data.waist_circumference.measured_at,
                        "hip_measurement_date": data.hip_circumference.measured_at,
                    },
                    source=source,
                    confidence=ConfidenceType.DERIVED,
                    display_kind="ratio",
                    calculated_at=calculated_at,
                )
            )
        if data.body_fat_percentage is not None:
            composition = calculate_body_composition(data.weight_kg, data.body_fat_percentage.value)
            confidence = (
                ConfidenceType.DERIVED
                if data.body_fat_percentage.source_type is MeasurementSource.MEASURED
                else ConfidenceType.ESTIMATED
            )
            inputs = {
                "weight_kg": data.weight_kg,
                "body_fat_percentage": data.body_fat_percentage.value,
                "measurement_date": data.body_fat_percentage.measured_at,
                "measurement_source": data.body_fat_percentage.source_type.value,
            }
            limitation = (
                "Die Genauigkeit hängt wesentlich von der Qualität der Körperfettmessung ab; "
                "die Werte sind keine Diagnose."
            )
            metrics.extend(
                (
                    self._metric(
                        code="body_composition.fat_mass_kg",
                        raw=composition.fat_mass_kg,
                        unit="kg",
                        method="weight_times_body_fat_fraction",
                        explanation="Körpergewicht multipliziert mit dem Körperfettanteil.",
                        limitations=limitation,
                        inputs=inputs,
                        source=source,
                        confidence=confidence,
                        display_kind="mass_kg",
                        calculated_at=calculated_at,
                    ),
                    self._metric(
                        code="body_composition.fat_free_mass_kg",
                        raw=composition.fat_free_mass_kg,
                        unit="kg",
                        method="weight_minus_fat_mass",
                        explanation="Körpergewicht abzüglich der berechneten Fettmasse.",
                        limitations=limitation,
                        inputs={**inputs, "fat_mass_kg": composition.fat_mass_kg},
                        source=source,
                        confidence=confidence,
                        display_kind="mass_kg",
                        calculated_at=calculated_at,
                    ),
                )
            )

    def _append_resting_metrics(
        self,
        metrics: list[MetricResult],
        data: AssessmentInput,
        resting: RestingEnergyCalculation,
        calculated_at: datetime,
    ) -> None:
        measured = resting.measured_value
        inputs: dict[str, Any] = {
            "weight_kg": data.weight_kg,
            "height_cm": data.height_cm,
            "age_years": data.age_years,
            "physiological_category": data.physiological_category.value,
        }
        confidence = ConfidenceType.ESTIMATED
        explanation = "Der Ruheenergieverbrauch wurde mit der Mifflin-St.-Jeor-Gleichung geschätzt."
        if measured:
            inputs.update(
                {
                    "measured_ree_kcal_per_day": measured.value,
                    "measurement_date": measured.measured_at,
                    "measurement_source": measured.source_type.value,
                }
            )
            confidence = ConfidenceType.MEASURED
            explanation = (
                "Der angegebene gemessene Ruheenergieverbrauch wird bevorzugt. Die "
                "Formelschätzung bleibt getrennt zum transparenten Vergleich erhalten."
            )
        metrics.append(
            self._metric(
                code="energy.resting_energy",
                raw=resting.selected_kcal_per_day,
                unit="kcal/Tag",
                method=resting.selected_method_id,
                explanation=explanation,
                limitations=(
                    "Messbedingungen und Messverfahren beeinflussen einen Messwert; eine "
                    "Formel ist stets nur eine Schätzung."
                ),
                inputs=inputs,
                source=self.references.source_metadata("mifflin_st_jeor_1990"),
                confidence=confidence,
                display_kind="energy_kcal",
                calculated_at=calculated_at,
            )
        )
        if measured:
            metrics.append(
                self._metric(
                    code="energy.resting_energy_formula_comparison",
                    raw=resting.formula_estimate_kcal_per_day,
                    unit="kcal/Tag",
                    method=resting.formula_id,
                    explanation=(
                        "Separate Mifflin-St.-Jeor-Schätzung zum Vergleich mit dem verwendeten "
                        "Messwert; sie ersetzt den Messwert nicht."
                    ),
                    limitations="Die Gleichung schätzt den individuellen Ruheenergieverbrauch.",
                    inputs={
                        "weight_kg": data.weight_kg,
                        "height_cm": data.height_cm,
                        "age_years": data.age_years,
                        "physiological_category": data.physiological_category.value,
                    },
                    source=self.references.source_metadata("mifflin_st_jeor_1990"),
                    confidence=ConfidenceType.ESTIMATED,
                    display_kind="energy_kcal",
                    calculated_at=calculated_at,
                )
            )

    def _pal_metric(
        self, data: AssessmentInput, pal: PalCalculation, calculated_at: datetime
    ) -> MetricResult:
        return self._metric(
            code="activity.pal",
            raw=pal.final_midpoint,
            lower=pal.final_minimum,
            upper=pal.final_maximum,
            unit="PAL",
            method=pal.method_id,
            explanation=pal.explanation_de,
            limitations=(
                "PAL ist eine transparente Aktivitätsschätzung, kein klinisch validiertes "
                "Konfidenzintervall. Alltag und Training können von Woche zu Woche abweichen."
            ),
            inputs={
                "activity_category": data.activity_category.value,
                "base_pal_minimum": pal.base_minimum,
                "base_pal_midpoint": pal.base_midpoint,
                "base_pal_maximum": pal.base_maximum,
                "sport_adjustment": pal.sport_adjustment,
                "qualifying_sessions": pal.qualifying_sessions,
                "total_weekly_exercise_minutes": pal.total_weekly_exercise_minutes,
                "manual_pal_override": pal.manual_override,
                "manual_override_includes_sport": (
                    self.rules.pal.manual_override_includes_all_activity
                ),
            },
            source=self.references.source_metadata("dge_pal_reference"),
            application_rule=pal.method_id,
            confidence=ConfidenceType.ESTIMATED,
            display_kind="pal",
            calculated_at=calculated_at,
        )

    def _maintenance_metric(
        self,
        resting: RestingEnergyCalculation,
        pal: PalCalculation,
        maintenance: EnergyRange,
        calculated_at: datetime,
    ) -> MetricResult:
        return self._metric(
            code="energy.maintenance",
            raw=maintenance.midpoint,
            lower=maintenance.lower,
            upper=maintenance.upper,
            unit="kcal/Tag",
            method="resting_energy_times_pal_range",
            explanation=(
                "Ruheenergieverbrauch multipliziert mit unterem, mittlerem und oberem PAL-Wert."
            ),
            limitations=(
                "Der Bereich ist eine Schätzung und kein klinisch validiertes "
                "Konfidenzintervall. Der tatsächliche Energiebedarf kann abweichen."
            ),
            inputs={
                "resting_energy_kcal": resting.selected_kcal_per_day,
                "pal_minimum": pal.final_minimum,
                "pal_midpoint": pal.final_midpoint,
                "pal_maximum": pal.final_maximum,
            },
            source=self.references.source_metadata("dge_pal_reference"),
            confidence=ConfidenceType.ESTIMATED,
            display_kind="energy_kcal",
            calculated_at=calculated_at,
        )

    def _goal_energy_metric(
        self,
        goal: GoalEnergyCalculation,
        maintenance: EnergyRange,
        calculated_at: datetime,
    ) -> MetricResult:
        energy_range = goal.energy_range
        return self._metric(
            code="energy.goal_target",
            raw=None if energy_range is None else energy_range.midpoint,
            lower=None if energy_range is None else energy_range.lower,
            upper=None if energy_range is None else energy_range.upper,
            unit="kcal/Tag",
            method=goal.method_id,
            explanation=goal.explanation_de,
            limitations=(
                "Anpassungsprozentsätze sind konservative MVP-Anwendungsregeln, keine DGE-Werte. "
                "Sie versprechen weder eine genaue Gewichtsänderung noch ein Zieldatum."
            ),
            inputs={
                "maintenance_lower_kcal": maintenance.lower,
                "maintenance_midpoint_kcal": maintenance.midpoint,
                "maintenance_upper_kcal": maintenance.upper,
                "configured_adjustment_percent": goal.configured_adjustment_percent,
                "applied_adjustment_percent": goal.applied_adjustment_percent,
                "deficit_was_capped": goal.deficit_was_capped,
                "ree_floor_was_applied": goal.ree_floor_was_applied,
            },
            source=self._application_only_source(),
            application_rule=goal.method_id,
            confidence=ConfidenceType.ESTIMATED,
            display_kind="energy_kcal",
            calculated_at=calculated_at,
        )

    def _goal_safety_flags(self, goal: GoalEnergyCalculation) -> tuple[SafetyFlag, ...]:
        flags: list[SafetyFlag] = []
        if goal.deficit_was_capped:
            flags.append(
                SafetyFlag(
                    code="ENERGY_DEFICIT_CAPPED",
                    severity=SafetySeverity.WARNING,
                    explanation_de="Ein angefragtes Defizit über 20 % wurde auf 20 % begrenzt.",
                    recommended_action_de=(
                        "Nutze den konservativen Bereich als Schätzung und hole bei Unsicherheit "
                        "fachlichen Rat ein."
                    ),
                )
            )
        if goal.ree_floor_was_applied:
            flags.append(
                SafetyFlag(
                    code="ENERGY_TARGET_BELOW_REE",
                    severity=SafetySeverity.WARNING,
                    explanation_de=(
                        "Der rechnerische Zielwert hätte den geschätzten oder gemessenen "
                        "Ruheenergieverbrauch unterschritten und wurde angehoben."
                    ),
                    recommended_action_de=(
                        "Eine stärkere Reduktion wird nicht automatisch vorgeschlagen. Besprich "
                        "weitergehende Ziele mit einer qualifizierten Fachperson."
                    ),
                )
            )
        if goal.aggressive_requested_change:
            flags.append(
                SafetyFlag(
                    code="AGGRESSIVE_REQUESTED_WEIGHT_CHANGE",
                    severity=SafetySeverity.WARNING,
                    explanation_de=(
                        "Die gewünschte wöchentliche Gewichtsänderung überschreitet die "
                        "konservative MVP-Warnschwelle von 1,0 kg pro Woche."
                    ),
                    recommended_action_de=(
                        "Die Rate wird nicht garantiert oder automatisch in ein größeres Defizit "
                        "übersetzt; ziehe fachliche Begleitung in Betracht."
                    ),
                )
            )
        if goal.requested_weekly_rate_was_not_used:
            flags.append(
                SafetyFlag(
                    code="REQUESTED_WEEKLY_RATE_NOT_MODELED",
                    severity=SafetySeverity.INFO,
                    explanation_de=(
                        "Die gewünschte Wochenrate wurde gespeichert, aber nicht als garantierte "
                        "Gewichts- oder Zeitprognose verwendet."
                    ),
                    recommended_action_de="Beobachte reale Verläufe; die Schätzung kann abweichen.",
                )
            )
        return tuple(flags)

    def _append_protein_metrics(
        self,
        metrics: list[MetricResult],
        data: AssessmentInput,
        protein: ProteinCalculation,
        calculated_at: datetime,
    ) -> None:
        source = (
            self.references.source_metadata(protein.scientific_reference_identifier)
            if protein.scientific_reference_identifier
            else self._unavailable_source()
        )
        common_inputs = {
            "weight_kg": data.weight_kg,
            "age_years": data.age_years,
            "weekly_training_hours": protein.weekly_training_hours,
            "goal_type": data.goal.goal_type.value,
            "athletic_range_eligible": protein.athletic_range_eligible,
            "athletic_range_suppressed_for_safety": (protein.athletic_range_suppressed_for_safety),
        }
        metrics.extend(
            (
                self._metric(
                    code="protein.grams_per_kg",
                    raw=protein.default_g_per_kg,
                    lower=protein.minimum_g_per_kg,
                    upper=protein.upper_g_per_kg,
                    unit="g/kg/Tag",
                    method=protein.selection_rule_id,
                    explanation=protein.explanation_de,
                    limitations=(
                        "Referenz- und Sportbereiche gelten für allgemein gesunde Personen. Der "
                        "Wert ist keine medizinische Ernährungstherapie."
                    ),
                    inputs=common_inputs,
                    source=source,
                    application_rule=protein.selection_rule_id,
                    confidence=ConfidenceType.REFERENCE_TARGET,
                    display_kind="protein_g_per_kg",
                    calculated_at=calculated_at,
                ),
                self._metric(
                    code="protein.grams_per_day",
                    raw=protein.default_grams_per_day,
                    lower=protein.minimum_grams_per_day,
                    upper=protein.upper_grams_per_day,
                    unit="g/Tag",
                    method="protein_g_per_kg_times_body_weight",
                    explanation=(
                        f"{protein.explanation_de} Der ausgewählte g/kg-Wert wird mit dem "
                        "aktuellen Körpergewicht multipliziert."
                    ),
                    limitations=(
                        "Das Ergebnis ist ein berechneter Zielbereich und keine Diagnose oder "
                        "individuelle medizinische Vorgabe."
                    ),
                    inputs={
                        **common_inputs,
                        "minimum_g_per_kg": protein.minimum_g_per_kg,
                        "default_g_per_kg": protein.default_g_per_kg,
                        "upper_g_per_kg": protein.upper_g_per_kg,
                    },
                    source=source,
                    application_rule=protein.selection_rule_id,
                    confidence=ConfidenceType.REFERENCE_TARGET,
                    display_kind="grams",
                    calculated_at=calculated_at,
                ),
            )
        )

    def _append_macro_metrics(
        self, metrics: list[MetricResult], macro: Any, calculated_at: datetime
    ) -> None:
        source = self.references.source_metadata("dge_macronutrients")
        limitation = (
            "Das Standard-Mischkostprofil ist nicht für jede Person optimal und bildet keine "
            "ketogene oder therapeutische Kost ab."
        )
        common = {
            "energy_lower_kcal": macro.energy.lower,
            "energy_midpoint_kcal": macro.energy.midpoint,
            "energy_upper_kcal": macro.energy.upper,
            "protein_kcal_per_g": self.rules.macronutrients.protein_kcal_per_g,
            "carbohydrate_kcal_per_g": self.rules.macronutrients.carbohydrate_kcal_per_g,
            "fat_kcal_per_g": self.rules.macronutrients.fat_kcal_per_g,
        }
        rows = (
            ("macros.protein_grams", macro.protein_grams, None, None, "g/Tag", "grams"),
            (
                "macros.protein_energy_percent",
                macro.protein_energy_percent,
                None,
                None,
                "% Energie",
                "percentage",
            ),
            (
                "macros.fat_grams",
                macro.fat_grams,
                macro.fat_grams_lower,
                macro.fat_grams_upper,
                "g/Tag",
                "grams",
            ),
            (
                "macros.fat_energy_percent",
                macro.fat_energy_percent,
                None,
                None,
                "% Energie",
                "percentage",
            ),
            (
                "macros.saturated_fat_max_grams",
                macro.saturated_fat_max_grams,
                None,
                None,
                "g/Tag",
                "grams",
            ),
            (
                "macros.saturated_fat_max_energy_percent",
                macro.saturated_fat_max_energy_percent,
                None,
                None,
                "% Energie",
                "percentage",
            ),
            (
                "macros.carbohydrate_grams",
                macro.carbohydrate_grams,
                macro.carbohydrate_grams_lower,
                macro.carbohydrate_grams_upper,
                "g/Tag",
                "grams",
            ),
            (
                "macros.carbohydrate_energy_percent",
                macro.carbohydrate_energy_percent,
                None,
                None,
                "% Energie",
                "percentage",
            ),
            (
                "macros.energy_sum",
                macro.macro_energy_sum_kcal,
                None,
                None,
                "kcal/Tag",
                "energy_kcal",
            ),
        )
        for code, raw, lower, upper, unit, display_kind in rows:
            metrics.append(
                self._metric(
                    code=code,
                    raw=raw,
                    lower=lower,
                    upper=upper,
                    unit=unit,
                    method="macro_energy_balance_4_4_9",
                    explanation=(
                        "Protein und Kohlenhydrate werden mit 4 kcal/g, Fett mit 9 kcal/g "
                        "berechnet; Kohlenhydrate erhalten die verbleibende Energie."
                    ),
                    limitations=limitation,
                    inputs={
                        **common,
                        "protein_grams": macro.protein_grams,
                        "fat_energy_percent": macro.fat_energy_percent,
                        "saturated_fat_max_energy_percent": (
                            macro.saturated_fat_max_energy_percent
                        ),
                    },
                    source=source,
                    application_rule="standard_mixed_diet_macro_distribution",
                    confidence=ConfidenceType.DERIVED,
                    display_kind=display_kind,
                    calculated_at=calculated_at,
                )
            )

    def _append_unavailable_macros_and_fiber(
        self, metrics: list[MetricResult], calculated_at: datetime
    ) -> None:
        codes_and_units = (
            ("macros.protein_grams", "g/Tag", "grams"),
            ("macros.protein_energy_percent", "% Energie", "percentage"),
            ("macros.fat_grams", "g/Tag", "grams"),
            ("macros.fat_energy_percent", "% Energie", "percentage"),
            ("macros.saturated_fat_max_grams", "g/Tag", "grams"),
            (
                "macros.saturated_fat_max_energy_percent",
                "% Energie",
                "percentage",
            ),
            ("macros.carbohydrate_grams", "g/Tag", "grams"),
            ("macros.carbohydrate_energy_percent", "% Energie", "percentage"),
            ("macros.energy_sum", "kcal/Tag", "energy_kcal"),
            ("fiber.target", "g/Tag", "grams"),
        )
        for code, unit, display_kind in codes_and_units:
            metrics.append(
                self._metric(
                    code=code,
                    raw=None,
                    unit=unit,
                    method="target_withheld_without_supported_energy_target",
                    explanation=(
                        "Ohne einen unterstützten zielangepassten Energiebereich wird dieser "
                        "Zielwert nicht berechnet."
                    ),
                    limitations=(
                        "Das MVP ersetzt keine individuelle medizinische Ernährungsplanung."
                    ),
                    inputs={},
                    source=self._unavailable_source(),
                    application_rule="withhold_dependent_targets_unsupported_scope",
                    confidence=ConfidenceType.REFERENCE_TARGET,
                    display_kind=display_kind,
                    calculated_at=calculated_at,
                )
            )

    def _append_hydration_metrics(
        self, metrics: list[MetricResult], data: AssessmentInput, calculated_at: datetime
    ) -> None:
        hydration = calculate_hydration(data.age_years, self.references)
        source = (
            self.references.source_metadata(hydration.source_identifier)
            if hydration.source_identifier
            else self._unavailable_source()
        )
        limitations = (
            "Der Basiswert kann sich durch Sport, Temperatur, Erkrankung, Schwangerschaft, "
            "Stillzeit und individuellen Schweißverlust ändern. Das MVP berechnet weder "
            "Schweißersatz noch Elektrolyttherapie oder medizinische Dehydratationshinweise."
        )
        inputs = {"age_years": data.age_years, "special_adjustment_applied": False}
        for code, raw in (
            ("hydration.total_water", hydration.total_water_ml),
            ("hydration.beverages", hydration.beverages_ml),
            ("hydration.food", hydration.food_ml),
            ("hydration.oxidation_water", hydration.oxidation_water_ml),
        ):
            metrics.append(
                self._metric(
                    code=code,
                    raw=raw,
                    unit="ml/Tag",
                    method=hydration.method_id,
                    explanation=hydration.explanation_de,
                    limitations=limitations,
                    inputs=inputs,
                    source=source,
                    confidence=ConfidenceType.REFERENCE_TARGET,
                    display_kind="water_ml",
                    calculated_at=calculated_at,
                )
            )

    def _append_micronutrient_metrics(
        self,
        metrics: list[MetricResult],
        targets: tuple[MicronutrientTarget, ...],
        data: AssessmentInput,
        calculated_at: datetime,
    ) -> None:
        for target in targets:
            explanation = (
                f"{target.display_name_de}: offizieller DGE/ÖGE-Referenzwert der Kategorie "
                f"'{target.reference_value_category}'. Referenzwerttypen sind keine identischen "
                "strikten täglichen Schwellen."
                if target.available
                else target.unavailable_reason_de or "Nicht verfügbar."
            )
            limitation = (
                "Ein Referenzwert diagnostiziert weder einen Mangel noch eine Überversorgung. "
                "Der MVP bewertet keine tatsächliche Lebensmittelzufuhr."
                if target.available
                else (
                    "Es wird bewusst kein plausibel wirkender Ersatzwert und kein US-Referenzwert "
                    "eingesetzt."
                )
            )
            metrics.append(
                self._metric(
                    code=f"micronutrients.{target.nutrient_code}",
                    raw=target.value,
                    lower=target.lower_value,
                    upper=target.upper_value,
                    unit=target.unit,
                    method=(
                        "versioned_reference_value_lookup"
                        if target.available
                        else "reference_value_unavailable"
                    ),
                    explanation=explanation,
                    limitations=limitation,
                    inputs={
                        "age_years": data.age_years,
                        "physiological_category": data.physiological_category.value,
                        "pregnant": data.health_screening.pregnant,
                        "breastfeeding": data.health_screening.breastfeeding,
                    },
                    source=target.source_metadata,
                    confidence=ConfidenceType.REFERENCE_TARGET,
                    display_kind="micronutrient",
                    calculated_at=calculated_at,
                )
            )

    def _metric(
        self,
        *,
        code: str,
        raw: Decimal | None,
        unit: str,
        method: str,
        explanation: str,
        limitations: str,
        inputs: Mapping[str, Any],
        source: Mapping[str, Any],
        confidence: ConfidenceType,
        display_kind: str,
        calculated_at: datetime,
        lower: Decimal | None = None,
        upper: Decimal | None = None,
        application_rule: str | None = None,
    ) -> MetricResult:
        display = (
            "Nicht verfügbar"
            if raw is None
            else format_decimal_de(raw, self.rules.display_places(display_kind))
        )
        return MetricResult(
            metric_code=code,
            raw_value=raw,
            display_value=display,
            lower_value=lower,
            upper_value=upper,
            unit=unit,
            method_code=method,
            explanation_de=explanation,
            limitations_de=limitations,
            calculation_inputs=inputs,
            source_metadata=source,
            application_rule_identifier=(
                None if application_rule is None else f"{self.rules.identifier}:{application_rule}"
            ),
            confidence_type=confidence,
            calculated_at=calculated_at,
        )

    def _application_only_source(self) -> dict[str, Any]:
        return {
            "reference_set_identifier": self.references.metadata.identifier,
            "reference_set_version": self.references.metadata.version,
            "scientific_reference_identifier": None,
            "reference_kind": "application_rule",
            "note_de": "Produktregel; wird nicht als offizieller DGE-Referenzwert dargestellt.",
        }

    def _unavailable_source(self) -> dict[str, Any]:
        return {
            "reference_set_identifier": self.references.metadata.identifier,
            "reference_set_version": self.references.metadata.version,
            "scientific_reference_identifier": None,
            "reference_kind": "unavailable",
            "note_de": self.references.metadata.completeness_note_de,
        }


def build_default_engine() -> NutritionEngine:
    """Build a fresh immutable engine from the checked-in versioned seed files."""

    return NutritionEngine.from_seed_data()


def calculate_assessment(data: AssessmentInput, *, calculated_at: datetime) -> AssessmentResult:
    """Convenience entry point for API services and tests."""

    return build_default_engine().assess(data, calculated_at=calculated_at)


def _optional_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _deduplicate_flags(flags: list[SafetyFlag]) -> tuple[SafetyFlag, ...]:
    seen: set[str] = set()
    result: list[SafetyFlag] = []
    for flag in flags:
        if flag.code not in seen:
            seen.add(flag.code)
            result.append(flag)
    return tuple(result)
