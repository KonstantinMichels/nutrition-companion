from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.modules.nutrition_assessment.engine import (
    AssessmentInput,
    EngineInputError,
    HealthScreening,
    Measurement,
    NutritionGoal,
    SportActivity,
    SupportedScopeStatus,
    build_default_engine,
)
from app.modules.nutrition_assessment.engine.activity import calculate_pal
from app.modules.nutrition_assessment.engine.anthropometrics import (
    calculate_bmi,
    calculate_body_composition,
    calculate_waist_to_height_ratio,
    calculate_waist_to_hip_ratio,
)
from app.modules.nutrition_assessment.engine.energy_targets import (
    EnergyRange,
    calculate_goal_energy,
    calculate_tdee,
)
from app.modules.nutrition_assessment.engine.fiber import calculate_fiber
from app.modules.nutrition_assessment.engine.hydration import calculate_hydration
from app.modules.nutrition_assessment.engine.macronutrients import (
    calculate_macronutrients,
    calculate_protein,
)
from app.modules.nutrition_assessment.engine.numeric import NumericInputError
from app.modules.nutrition_assessment.engine.reference_data import load_reference_data
from app.modules.nutrition_assessment.engine.resting_energy import (
    MEASURED_REE_METHOD_ID,
    calculate_resting_energy,
    mifflin_st_jeor,
)
from app.modules.nutrition_assessment.engine.rules import load_application_rules

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def make_input(**overrides: object) -> AssessmentInput:
    values: dict[str, object] = {
        "age_years": 30,
        "height_cm": "180",
        "weight_kg": "80",
        "physiological_category": "reference_category_a",
        "activity_category": "mostly_seated",
        "goal": NutritionGoal("maintain_weight"),
    }
    values.update(overrides)
    return AssessmentInput(**values)  # type: ignore[arg-type]


def measured(value: str, unit: str, source: str = "measured") -> Measurement:
    return Measurement(value, unit, date(2026, 7, 1), source)


@pytest.fixture
def rules():
    return load_application_rules()


@pytest.fixture
def references():
    return load_reference_data()


@pytest.fixture
def engine():
    return build_default_engine()


def test_bmi_uses_unrounded_height_in_metres() -> None:
    assert calculate_bmi("80", "180") == Decimal("80") / Decimal("3.24")


def test_waist_ratios_known_fixture() -> None:
    assert calculate_waist_to_height_ratio("90", "180") == Decimal("0.5")
    assert calculate_waist_to_hip_ratio("80", "100") == Decimal("0.8")


def test_body_composition_known_fixture() -> None:
    result = calculate_body_composition("80", "25")
    assert result.fat_mass_kg == Decimal("20")
    assert result.fat_free_mass_kg == Decimal("60")


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("reference_category_a", Decimal("1780.00")),
        ("reference_category_b", Decimal("1614.00")),
    ],
)
def test_both_mifflin_st_jeor_variants(category: str, expected: Decimal) -> None:
    assert (
        mifflin_st_jeor(
            weight_kg="80",
            height_cm="180",
            age_years=30,
            physiological_category=category,
        )
        == expected
    )


def test_measured_resting_energy_overrides_but_retains_formula_estimate() -> None:
    data = make_input(
        measured_resting_energy_expenditure=measured("1650", "kcal/day", "device_estimate")
    )
    result = calculate_resting_energy(data)
    assert result.selected_kcal_per_day == Decimal("1650")
    assert result.selected_method_id == MEASURED_REE_METHOD_ID
    assert result.formula_estimate_kcal_per_day == Decimal("1780.00")
    assert result.measured_value is not None
    assert result.measured_value.source_type.value == "device_estimate"


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("mostly_seated", ("1.4", "1.45", "1.5")),
        ("seated_with_walking", ("1.6", "1.65", "1.7")),
        ("mostly_standing_walking", ("1.8", "1.85", "1.9")),
        ("physically_demanding", ("2.0", "2.2", "2.4")),
    ],
)
def test_pal_category_selection(category: str, expected: tuple[str, str, str], rules) -> None:
    result = calculate_pal(make_input(activity_category=category), rules)
    assert (result.final_minimum, result.final_midpoint, result.final_maximum) == tuple(
        Decimal(value) for value in expected
    )


def test_qualifying_sport_adjustment_is_added_once(rules) -> None:
    data = make_input(sports=[SportActivity("running", "4", "45", "moderate")])
    result = calculate_pal(data, rules)
    assert result.qualifying_sessions == Decimal("4")
    assert result.sport_adjustment == Decimal("0.3")
    assert (result.final_minimum, result.final_midpoint, result.final_maximum) == (
        Decimal("1.7"),
        Decimal("1.75"),
        Decimal("1.8"),
    )


def test_no_unverified_partial_sport_adjustment(rules) -> None:
    data = make_input(sports=[SportActivity("running", "3", "45", "moderate")])
    result = calculate_pal(data, rules)
    assert result.sport_adjustment == 0
    assert result.final_midpoint == Decimal("1.45")


def test_manual_pal_override_is_final_and_prevents_double_counting(rules) -> None:
    data = make_input(
        manual_pal_override="1.72",
        sports=[SportActivity("running", "5", "60", "vigorous")],
    )
    result = calculate_pal(data, rules)
    assert result.manual_override == Decimal("1.72")
    assert result.sport_adjustment == 0
    assert result.final_minimum == result.final_midpoint == result.final_maximum == Decimal("1.72")
    assert "nicht ein zweites Mal" in result.explanation_de


def test_pal_upper_boundary_is_applied_transparently(rules) -> None:
    data = make_input(
        activity_category="physically_demanding",
        sports=[SportActivity("running", "4", "45", "vigorous")],
    )
    result = calculate_pal(data, rules)
    assert result.sport_adjustment == Decimal("0.3")
    assert result.final_minimum == Decimal("2.3")
    assert result.final_midpoint == result.final_maximum == Decimal("2.4")
    assert result.final_range_was_capped


def test_tdee_lower_midpoint_and_upper_are_ree_times_pal(rules) -> None:
    pal = calculate_pal(make_input(), rules)
    result = calculate_tdee("1780", pal)
    assert result == EnergyRange(Decimal("2492.0"), Decimal("2581.00"), Decimal("2670.0"))


@pytest.mark.parametrize(
    ("goal", "intensity", "expected_percent"),
    [
        ("maintain_weight", None, "0"),
        ("general_health", None, "0"),
        ("athletic_performance", None, "0"),
        ("lose_weight", "mild", "-10"),
        ("lose_weight", "moderate", "-15"),
        ("gain_weight", "mild", "5"),
        ("gain_weight", "moderate", "10"),
    ],
)
def test_goal_adjustment_application_rules(
    goal: str, intensity: str | None, expected_percent: str, rules
) -> None:
    maintenance = EnergyRange(Decimal("2000"), Decimal("2200"), Decimal("2400"))
    result = calculate_goal_energy(
        maintenance=maintenance,
        resting_energy_kcal="1200",
        goal_type=goal,
        intensity=intensity,
        rules=rules,
    )
    factor = Decimal(1) + Decimal(expected_percent) / Decimal(100)
    assert result.applied_adjustment_percent == Decimal(expected_percent)
    assert result.energy_range == EnergyRange(
        maintenance.lower * factor,
        maintenance.midpoint * factor,
        maintenance.upper * factor,
    )


def test_deficit_cap_is_enforced_and_recorded(rules) -> None:
    result = calculate_goal_energy(
        maintenance=EnergyRange(Decimal("2000"), Decimal("2200"), Decimal("2400")),
        resting_energy_kcal="1000",
        goal_type="lose_weight",
        intensity="moderate",
        rules=rules,
        requested_adjustment_percent="-35",
    )
    assert result.configured_adjustment_percent == Decimal("-35")
    assert result.applied_adjustment_percent == Decimal("-20")
    assert result.deficit_was_capped
    assert result.energy_range is not None
    assert result.energy_range.midpoint == Decimal("1760.0")


def test_target_below_ree_is_warned_and_floored(rules) -> None:
    result = calculate_goal_energy(
        maintenance=EnergyRange(Decimal("1000"), Decimal("1200"), Decimal("1400")),
        resting_energy_kcal="1500",
        goal_type="lose_weight",
        intensity="moderate",
        rules=rules,
    )
    assert result.ree_floor_was_applied
    assert result.energy_range == EnergyRange(Decimal("1500"), Decimal("1500"), Decimal("1500"))


def test_aggressive_requested_weekly_rate_is_only_a_warning_input(rules) -> None:
    result = calculate_goal_energy(
        maintenance=EnergyRange(Decimal("2000"), Decimal("2100"), Decimal("2200")),
        resting_energy_kcal="1200",
        goal_type="lose_weight",
        intensity="mild",
        rules=rules,
        requested_weekly_rate_kg="1.2",
    )
    assert result.aggressive_requested_change
    assert result.requested_weekly_rate_was_not_used
    assert result.applied_adjustment_percent == Decimal("-10")


def test_standard_protein_target_is_not_increased_at_five_hours(rules) -> None:
    data = make_input(sports=[SportActivity("running", "5", "60", "moderate")])
    result = calculate_protein(data, rules, supported_scope=True)
    assert result.weekly_training_hours == Decimal("5")
    assert not result.athletic_range_eligible
    assert result.default_g_per_kg == Decimal("0.8")
    assert result.default_grams_per_day == Decimal("64.0")


def test_verified_boundary_age_protein_references(rules) -> None:
    age_18_a = calculate_protein(make_input(age_years=18), rules, supported_scope=True)
    age_18_b = calculate_protein(
        make_input(age_years=18, physiological_category="reference_category_b"),
        rules,
        supported_scope=True,
    )
    age_65 = calculate_protein(make_input(age_years=65), rules, supported_scope=True)
    assert age_18_a.default_g_per_kg == Decimal("0.9")
    assert age_18_b.default_g_per_kg == Decimal("0.8")
    assert age_65.default_g_per_kg == Decimal("1.0")


def test_athletic_endurance_protein_range_selects_lower_part(rules) -> None:
    data = make_input(sports=[SportActivity("running", "6", "60", "moderate")])
    result = calculate_protein(data, rules, supported_scope=True)
    assert result.athletic_range_eligible
    assert result.minimum_g_per_kg == Decimal("1.2")
    assert result.default_g_per_kg == Decimal("1.4")
    assert result.upper_g_per_kg == Decimal("2.0")


@pytest.mark.parametrize(
    ("goal", "sport", "selected"),
    [
        (NutritionGoal("lose_weight", "mild"), "running", Decimal("1.8")),
        (NutritionGoal("gain_weight", "mild"), "running", Decimal("1.7")),
        (NutritionGoal("maintain_weight"), "strength_training", Decimal("1.7")),
        (NutritionGoal("maintain_weight"), "team_sport", Decimal("1.5")),
    ],
)
def test_athletic_protein_selection_is_not_always_upper_limit(
    goal: NutritionGoal, sport: str, selected: Decimal, rules
) -> None:
    data = make_input(goal=goal, sports=[SportActivity(sport, "6", "60", "vigorous")])
    result = calculate_protein(data, rules, supported_scope=True)
    assert result.default_g_per_kg == selected
    assert result.default_g_per_kg != result.upper_g_per_kg


def test_high_protein_is_suppressed_and_flagged_with_kidney_condition(engine) -> None:
    data = make_input(
        sports=[SportActivity("strength_training", "6", "60", "vigorous")],
        health_screening=HealthScreening(kidney_disease=True),
    )
    result = engine.assess(data, calculated_at=NOW)
    assert result.supported_scope_status is SupportedScopeStatus.UNSUPPORTED
    assert result.metric("protein.grams_per_kg").raw_value == Decimal("0.8")
    assert {flag.code for flag in result.safety_flags} >= {
        "UNSUPPORTED_KIDNEY_DISEASE",
        "HIGH_PROTEIN_KIDNEY_CONDITION",
    }


def test_macro_grams_percentages_and_energy_are_consistent(rules) -> None:
    macro = calculate_macronutrients(
        energy=EnergyRange(Decimal("2000"), Decimal("2000"), Decimal("2000")),
        protein_grams=Decimal("100"),
        rules=rules,
    )
    assert macro.fat_grams == Decimal("2000") * Decimal("0.30") / Decimal("9")
    assert macro.carbohydrate_grams == Decimal("250")
    assert macro.protein_energy_percent == Decimal("20")
    assert macro.fat_energy_percent == Decimal("30")
    assert macro.carbohydrate_energy_percent == Decimal("50")
    assert macro.macro_energy_sum_kcal == Decimal("2000")
    assert macro.carbohydrate_below_standard_guidance


def test_macro_energy_consistency_across_energy_range(rules) -> None:
    macro = calculate_macronutrients(
        energy=EnergyRange(Decimal("1800"), Decimal("2100"), Decimal("2400")),
        protein_grams=Decimal("80"),
        rules=rules,
    )
    for energy, fat, carbohydrate in (
        (Decimal("1800"), macro.fat_grams_lower, macro.carbohydrate_grams_lower),
        (Decimal("2100"), macro.fat_grams, macro.carbohydrate_grams),
        (Decimal("2400"), macro.fat_grams_upper, macro.carbohydrate_grams_upper),
    ):
        assert Decimal("80") * 4 + fat * 9 + carbohydrate * 4 == energy


def test_fiber_uses_absolute_minimum_at_2000_kcal(rules) -> None:
    result = calculate_fiber(EnergyRange(Decimal("2000"), Decimal("2000"), Decimal("2000")), rules)
    assert result.energy_relative_g == Decimal("29.2")
    assert result.selected_g == Decimal("30")


def test_fiber_uses_energy_relative_rule_when_higher(rules) -> None:
    result = calculate_fiber(EnergyRange(Decimal("3000"), Decimal("3000"), Decimal("3000")), rules)
    assert result.selected_g == Decimal("43.8")


@pytest.mark.parametrize(
    ("age", "beverages", "food", "oxidation", "total"),
    [
        (18, "1530", "920", "350", "2800"),
        (20, "1470", "890", "340", "2700"),
        (30, "1410", "860", "330", "2600"),
        (60, "1230", "740", "280", "2250"),
        (65, "1310", "680", "260", "2250"),
    ],
)
def test_hydration_baseline_uses_verified_age_bands(
    age: int, beverages: str, food: str, oxidation: str, total: str, references
) -> None:
    result = calculate_hydration(age, references)
    assert result.available
    assert result.beverages_ml == Decimal(beverages)
    assert result.food_ml == Decimal(food)
    assert result.oxidation_water_ml == Decimal(oxidation)
    assert result.total_water_ml == Decimal(total)
    assert result.beverages_ml + result.food_ml + result.oxidation_water_ml == result.total_water_ml


def test_reference_value_lookup_selects_age_and_category(references) -> None:
    category_a = references.lookup_micronutrient(
        "vitamin_c", age_years=30, physiological_category="reference_category_a"
    )
    category_b = references.lookup_micronutrient(
        "vitamin_c", age_years=30, physiological_category="reference_category_b"
    )
    assert category_a.value is not None and category_a.value.value == Decimal("110")
    assert category_b.value is not None and category_b.value.value == Decimal("95")
    assert category_a.value.reference_value_category == "recommended_intake"


def test_missing_reference_value_is_honestly_unavailable(references) -> None:
    lookup = references.lookup_micronutrient(
        "magnesium", age_years=30, physiological_category="reference_category_a"
    )
    assert not lookup.available
    assert lookup.value is None
    assert "nicht" in (lookup.unavailable_reason_de or "").lower()


def test_age_specific_gap_is_not_filled_with_an_adult_placeholder(references) -> None:
    lookup = references.lookup_micronutrient(
        "vitamin_a", age_years=18, physiological_category="reference_category_a"
    )
    assert not lookup.available


def test_pregnancy_reference_is_not_silently_substituted(references) -> None:
    lookup = references.lookup_micronutrient(
        "vitamin_d",
        age_years=30,
        physiological_category="reference_category_b",
        pregnant=True,
    )
    assert not lookup.available
    assert "Schwangerschaft" in (lookup.unavailable_reason_de or "")


@pytest.mark.parametrize(
    "health",
    [
        HealthScreening(pregnant=True),
        HealthScreening(breastfeeding=True),
        HealthScreening(diagnosed_eating_disorder=True),
        HealthScreening(diabetes=True),
        HealthScreening(kidney_disease=True),
        HealthScreening(liver_disease=True),
        HealthScreening(medically_prescribed_diet=True),
        HealthScreening(serious_metabolic_condition=True),
        HealthScreening(other_professional_nutrition_condition=True),
    ],
)
def test_each_unsupported_health_screen_blocks_goal_target(health: HealthScreening, engine) -> None:
    result = engine.assess(make_input(health_screening=health), calculated_at=NOW)
    assert result.supported_scope_status is SupportedScopeStatus.UNSUPPORTED
    assert result.metric("energy.goal_target").raw_value is None
    assert result.metric("macros.fat_grams").raw_value is None
    assert any(flag.severity.value == "blocking" for flag in result.safety_flags)


@pytest.mark.parametrize("age", [17, 66])
def test_age_outside_supported_scope(age: int, engine) -> None:
    result = engine.assess(make_input(age_years=age), calculated_at=NOW)
    assert result.supported_scope_status is SupportedScopeStatus.UNSUPPORTED
    assert "UNSUPPORTED_AGE" in {flag.code for flag in result.safety_flags}
    assert result.metric("energy.goal_target").raw_value is None


def test_supported_age_boundaries_are_in_scope(engine) -> None:
    assert engine.assess(
        make_input(age_years=18), calculated_at=NOW
    ).supported_scope_status.value == ("supported")
    assert engine.assess(
        make_input(age_years=65), calculated_at=NOW
    ).supported_scope_status.value == ("supported")


def test_full_assessment_includes_optional_anthropometrics_and_confidence(engine) -> None:
    data = make_input(
        body_fat_percentage=measured("25", "%", "user_estimate"),
        waist_circumference=measured("90", "cm"),
        hip_circumference=measured("100", "cm"),
    )
    result = engine.assess(data, calculated_at=NOW)
    assert result.metric("anthropometrics.waist_to_height_ratio").raw_value == Decimal("0.5")
    assert result.metric("anthropometrics.waist_to_hip_ratio").raw_value == Decimal("0.9")
    assert result.metric("body_composition.fat_mass_kg").raw_value == Decimal("20")
    assert result.metric("body_composition.fat_mass_kg").confidence_type.value == "estimated"


def test_every_metric_carries_required_transparency_metadata(engine) -> None:
    result = engine.assess(make_input(), calculated_at=NOW)
    for metric in result.metrics:
        assert metric.display_value
        assert metric.unit
        assert metric.method_code
        assert metric.explanation_de
        assert metric.limitations_de
        assert "reference_set_identifier" in metric.source_metadata
        assert metric.calculated_at == NOW


def test_no_premature_rounding_and_display_rounding_are_separate(engine) -> None:
    result = engine.assess(make_input(weight_kg="82.5", height_cm="177"), calculated_at=NOW)
    metric = result.metric("anthropometrics.bmi")
    expected = Decimal("82.5") / (Decimal("1.77") ** 2)
    assert metric.raw_value == expected
    assert metric.raw_value != Decimal(metric.display_value.replace(",", "."))
    assert metric.display_value == "26,3"


def test_deterministic_repeatability_includes_timestamp_from_caller(engine) -> None:
    data = make_input(
        sports=[SportActivity("running", "4", "45", "moderate")],
        goal=NutritionGoal("lose_weight", "mild"),
    )
    first = engine.assess(data, calculated_at=NOW)
    second = engine.assess(data, calculated_at=NOW)
    assert first == second
    assert first.to_dict() == second.to_dict()


def test_result_is_json_serializable_and_snapshot_preserves_decimals(engine) -> None:
    result = engine.assess(make_input(weight_kg="82.50"), calculated_at=NOW)
    encoded = json.dumps(result.to_dict(), ensure_ascii=False)
    assert '"weight_kg": "82.50"' in encoded
    assert '"reference_set_identifier": "dge_oege_v3_mvp_2026_05"' in encoded


def test_food_groups_are_structured_and_not_compliance_scores(engine) -> None:
    result = engine.assess(make_input(), calculated_at=NOW)
    codes = {item.code for item in result.food_groups}
    assert {
        "water_calorie_free_beverages",
        "vegetables",
        "fruit",
        "legumes",
        "nuts_seeds",
        "whole_grain_foods",
        "plant_oils",
        "dairy_or_alternatives",
        "fish",
        "meat_processed_meat",
        "highly_processed_discretionary",
    } == codes
    assert all("compliance" not in item.to_dict() for item in result.food_groups)


def test_all_requested_micronutrient_codes_are_returned(engine) -> None:
    result = engine.assess(make_input(), calculated_at=NOW)
    nutrient_metrics = [
        metric for metric in result.metrics if metric.metric_code.startswith("micronutrients.")
    ]
    assert len(nutrient_metrics) == 27
    assert result.metric("micronutrients.magnesium").display_value == "Nicht verfügbar"
    assert result.metric("micronutrients.vitamin_d").raw_value == Decimal("20")


def test_invalid_range_is_rejected_not_clamped(engine) -> None:
    with pytest.raises(EngineInputError) as error:
        engine.assess(make_input(height_cm="99"), calculated_at=NOW)
    assert error.value.issues[0].field == "height_cm"
    assert error.value.issues[0].code == "OUT_OF_RANGE"


def test_nan_and_infinity_are_rejected_at_typed_input_boundary() -> None:
    with pytest.raises(NumericInputError):
        make_input(weight_kg="NaN")
    with pytest.raises(NumericInputError):
        make_input(height_cm="Infinity")


def test_manual_pal_outside_allowed_range_is_rejected_not_clamped(engine) -> None:
    with pytest.raises(EngineInputError) as error:
        engine.assess(make_input(manual_pal_override="2.41"), calculated_at=NOW)
    assert {issue.field for issue in error.value.issues} == {"manual_pal_override"}


def test_assessment_timestamp_must_be_timezone_aware(engine) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        engine.assess(make_input(), calculated_at=datetime(2026, 7, 28, 12, 0))


def test_reference_and_rule_set_metadata_are_reproducible(engine) -> None:
    result = engine.assess(make_input(), calculated_at=NOW)
    assert result.reference_set_identifier == "dge_oege_v3_mvp_2026_05"
    assert result.reference_set_version == "3rd-edition-2025_erratum-2026-05_subset-v1"
    assert result.application_rule_set_identifier == "nutrition_companion_mvp_v1"
    assert result.application_rule_set_version == "v1"
    assert result.engine_version == "nutrition_engine_v1"


def test_persistence_metric_shape_keeps_raw_decimal(engine) -> None:
    metric = engine.assess(make_input(), calculated_at=NOW).metric("anthropometrics.bmi")
    payload = metric.to_persistence_dict()
    assert isinstance(payload["raw_value"], Decimal)
    assert payload["calculation_inputs"] == {"weight_kg": "80", "height_cm": "180"}
    assert payload["confidence_type"] == "derived"
