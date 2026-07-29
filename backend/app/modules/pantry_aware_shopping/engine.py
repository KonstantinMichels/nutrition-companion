from __future__ import annotations

from decimal import Decimal
from typing import Any


def calculate_target(
    *,
    combined_requirement: Decimal,
    pantry_available: Decimal,
    target_commitment: Decimal,
    other_commitment: Decimal,
) -> dict[str, Any]:
    global_need = max(
        combined_requirement - pantry_available - target_commitment - other_commitment,
        Decimal(0),
    )
    desired = max(combined_requirement - pantry_available - other_commitment, Decimal(0))
    change = desired - target_commitment
    if desired == 0 and pantry_available >= combined_requirement:
        state = "fully_covered_by_pantry"
    elif desired == 0 and other_commitment > 0:
        state = "covered_elsewhere"
    elif target_commitment == 0 and desired > 0:
        state = "create"
    elif change > 0:
        state = "increase"
    elif change < 0:
        state = "decrease"
    else:
        state = "unchanged"
    return {
        "global_additional_need": global_need,
        "desired_target_commitment": desired,
        "suggested_target_change": change,
        "target_change_state": state,
    }


def override_relation(purchase: Decimal | None, suggestion: Decimal) -> str | None:
    if purchase is None:
        return None
    if purchase < suggestion:
        return "below_suggestion"
    if purchase > suggestion:
        return "above_suggestion"
    return "matches_suggestion"
