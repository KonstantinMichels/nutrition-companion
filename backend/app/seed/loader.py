"""Strict JSON readers with no persistence-layer coupling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SEED_DIRECTORY = Path(__file__).resolve().parent


def _load_json(filename: str) -> dict[str, Any]:
    path = SEED_DIRECTORY / filename
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"seed document {filename} must contain a JSON object")
    return document


def load_application_rules_document() -> dict[str, Any]:
    return _load_json("application_rules.json")


def load_reference_values_document() -> dict[str, Any]:
    return _load_json("reference_values.json")


def load_food_groups_document() -> dict[str, Any]:
    return _load_json("food_groups.json")
