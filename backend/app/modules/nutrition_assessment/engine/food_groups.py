"""Structured DGE food-based recommendations for later meal planning."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.seed.loader import load_food_groups_document

from .numeric import as_decimal
from .result_models import FoodGroupRecommendation


def load_food_group_recommendations(
    document: Mapping[str, Any] | None = None,
) -> tuple[FoodGroupRecommendation, ...]:
    raw = dict(document or load_food_groups_document())
    source_raw = raw.get("source")
    if not isinstance(source_raw, dict):
        raise ValueError("food-groups source must be an object")
    source_metadata = {
        "scientific_reference_identifier": str(raw["identifier"]),
        "reference_version": str(raw["version"]),
        **source_raw,
    }
    recommendations_raw = raw.get("recommendations")
    if not isinstance(recommendations_raw, list) or not all(
        isinstance(item, dict) for item in recommendations_raw
    ):
        raise ValueError("food-groups recommendations must be a list of objects")
    recommendations = tuple(
        FoodGroupRecommendation(
            code=str(item["code"]),
            display_name_de=str(item["display_name_de"]),
            recommendation_de=str(item["recommendation_de"]),
            amount=_optional_decimal(item.get("amount")),
            unit=None if item.get("unit") is None else str(item["unit"]),
            frequency=str(item["frequency"]),
            minimum=_optional_decimal(item.get("minimum")),
            maximum=_optional_decimal(item.get("maximum")),
            combined_group_code=(
                None
                if item.get("combined_group_code") is None
                else str(item["combined_group_code"])
            ),
            source_metadata=source_metadata,
        )
        for item in recommendations_raw
    )
    if len({item.code for item in recommendations}) != len(recommendations):
        raise ValueError("food-group recommendation codes must be unique")
    return recommendations


def _optional_decimal(value: Any) -> Decimal | None:
    return None if value is None else as_decimal(value)
