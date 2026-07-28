"""Mifflin-St Jeor and measured resting-energy selection."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .input_models import AssessmentInput, Measurement, PhysiologicalCategory
from .numeric import DecimalLike, as_decimal

MIFFLIN_CATEGORY_A_FORMULA_ID = "mifflin_st_jeor_1990_reference_category_a"
MIFFLIN_CATEGORY_B_FORMULA_ID = "mifflin_st_jeor_1990_reference_category_b"
MEASURED_REE_METHOD_ID = "measured_resting_energy_expenditure_override"


def mifflin_st_jeor(
    *,
    weight_kg: DecimalLike,
    height_cm: DecimalLike,
    age_years: int,
    physiological_category: PhysiologicalCategory | str,
) -> Decimal:
    weight = as_decimal(weight_kg, field="weight_kg")
    height = as_decimal(height_cm, field="height_cm")
    category = PhysiologicalCategory(physiological_category)
    if weight <= 0 or height <= 0 or age_years <= 0:
        raise ValueError("Mifflin inputs must be positive")
    constant = (
        Decimal(5) if category is PhysiologicalCategory.REFERENCE_CATEGORY_A else Decimal(-161)
    )
    return Decimal(10) * weight + Decimal("6.25") * height - Decimal(5) * age_years + constant


def mifflin_formula_id(category: PhysiologicalCategory) -> str:
    return (
        MIFFLIN_CATEGORY_A_FORMULA_ID
        if category is PhysiologicalCategory.REFERENCE_CATEGORY_A
        else MIFFLIN_CATEGORY_B_FORMULA_ID
    )


@dataclass(frozen=True, slots=True)
class RestingEnergyCalculation:
    selected_kcal_per_day: Decimal
    selected_method_id: str
    measured_value: Measurement | None
    formula_estimate_kcal_per_day: Decimal
    formula_id: str

    @property
    def uses_measured_override(self) -> bool:
        return self.measured_value is not None


def calculate_resting_energy(data: AssessmentInput) -> RestingEnergyCalculation:
    estimate = mifflin_st_jeor(
        weight_kg=data.weight_kg,
        height_cm=data.height_cm,
        age_years=data.age_years,
        physiological_category=data.physiological_category,
    )
    measured = data.measured_resting_energy_expenditure
    return RestingEnergyCalculation(
        selected_kcal_per_day=measured.value if measured else estimate,
        selected_method_id=MEASURED_REE_METHOD_ID
        if measured
        else mifflin_formula_id(data.physiological_category),
        measured_value=measured,
        formula_estimate_kcal_per_day=estimate,
        formula_id=mifflin_formula_id(data.physiological_category),
    )
