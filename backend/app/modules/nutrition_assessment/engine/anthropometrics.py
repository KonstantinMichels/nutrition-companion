"""Pure anthropometric calculations with full intermediate precision."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .numeric import DecimalLike, as_decimal


def calculate_bmi(weight_kg: DecimalLike, height_cm: DecimalLike) -> Decimal:
    weight = as_decimal(weight_kg, field="weight_kg")
    height = as_decimal(height_cm, field="height_cm")
    if weight <= 0 or height <= 0:
        raise ValueError("weight and height must be positive")
    height_m = height / Decimal(100)
    return weight / (height_m * height_m)


def calculate_waist_to_height_ratio(waist_cm: DecimalLike, height_cm: DecimalLike) -> Decimal:
    waist = as_decimal(waist_cm, field="waist_cm")
    height = as_decimal(height_cm, field="height_cm")
    if waist <= 0 or height <= 0:
        raise ValueError("waist and height must be positive")
    return waist / height


def calculate_waist_to_hip_ratio(waist_cm: DecimalLike, hip_cm: DecimalLike) -> Decimal:
    waist = as_decimal(waist_cm, field="waist_cm")
    hip = as_decimal(hip_cm, field="hip_cm")
    if waist <= 0 or hip <= 0:
        raise ValueError("waist and hip must be positive")
    return waist / hip


@dataclass(frozen=True, slots=True)
class BodyComposition:
    fat_mass_kg: Decimal
    fat_free_mass_kg: Decimal


def calculate_body_composition(
    weight_kg: DecimalLike, body_fat_percentage: DecimalLike
) -> BodyComposition:
    weight = as_decimal(weight_kg, field="weight_kg")
    percentage = as_decimal(body_fat_percentage, field="body_fat_percentage")
    if weight <= 0 or not 0 <= percentage <= 100:
        raise ValueError("weight must be positive and body-fat percentage must be 0 to 100")
    fat_mass = weight * percentage / Decimal(100)
    return BodyComposition(fat_mass_kg=fat_mass, fat_free_mass_kg=weight - fat_mass)
