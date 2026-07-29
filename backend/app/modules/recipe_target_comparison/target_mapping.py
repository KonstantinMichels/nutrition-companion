from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TargetKind = Literal["minimum", "maximum", "range", "reference"]


@dataclass(frozen=True, slots=True)
class TargetMapping:
    nutrient_code: str
    target_kind: TargetKind


EXPLICIT_TARGETS: dict[str, TargetMapping] = {
    "energy.goal_target": TargetMapping("energy_kcal", "range"),
    "protein.grams_per_day": TargetMapping("protein", "range"),
    "macros.fat_grams": TargetMapping("fat", "range"),
    "macros.carbohydrate_grams": TargetMapping("carbohydrate", "range"),
    "macros.saturated_fat_max_grams": TargetMapping("saturated_fat", "maximum"),
    "fiber.target": TargetMapping("fiber", "minimum"),
}


def mapping_for(metric_code: str) -> TargetMapping | None:
    explicit = EXPLICIT_TARGETS.get(metric_code)
    if explicit is not None:
        return explicit
    if metric_code.startswith("micronutrients."):
        return TargetMapping(metric_code.removeprefix("micronutrients."), "reference")
    return None
