from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.modules.meal_plan_automation.models import (
    AutomationApplication,
    AutomationMealSlot,
    AutomationPreferences,
)
from app.modules.meal_plan_automation.schemas import PreferencesWrite, SlotWrite


def err(code: str, msg: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=msg, status_code=status)


def get(session: Session, owner: UUID, pid: UUID) -> AutomationPreferences:
    value = session.scalar(
        select(AutomationPreferences)
        .where(AutomationPreferences.id == pid, AutomationPreferences.owner_profile_id == owner)
        .options(selectinload(AutomationPreferences.slots))
    )
    if value is None:
        raise err(
            "AUTOMATION_PREFERENCES_NOT_FOUND", "Die Einstellungen wurden nicht gefunden.", 404
        )
    return value


def serialize(x: AutomationPreferences) -> dict[str, Any]:
    return {
        "id": x.id,
        "name": x.name,
        "is_default": x.is_default,
        "assessment_selection_mode": x.assessment_selection_mode,
        "selected_assessment_id": x.selected_assessment_id,
        "generation_scope_default": x.generation_scope_default,
        "pantry_preference": x.pantry_preference,
        "shopping_effort_preference": x.shopping_effort_preference,
        "maximum_recipe_repetitions_per_week": x.maximum_recipe_repetitions_per_week,
        "minimum_days_between_same_recipe": x.minimum_days_between_same_recipe,
        "maximum_preparation_time_minutes": x.maximum_preparation_time_minutes,
        "allow_incomplete_basic_nutrition": x.allow_incomplete_basic_nutrition,
        "allow_archived_recipe_candidates": x.allow_archived_recipe_candidates,
        "include_optional_recipe_ingredients": x.include_optional_recipe_ingredients,
        "enabled_recipe_tag_codes": x.enabled_recipe_tag_codes,
        "excluded_recipe_tag_codes": x.excluded_recipe_tag_codes,
        "excluded_recipe_ids": x.excluded_recipe_ids,
        "scoring_weights": x.scoring_weights,
        "is_archived": x.is_archived,
        "updated_at": x.updated_at,
        "slots": [
            {
                "id": s.id,
                "slot_code": s.slot_code,
                "meal_type": s.meal_type,
                "custom_name": s.custom_name,
                "default_time": s.default_time,
                "position": s.position,
                "is_enabled": s.is_enabled,
                "allowed_recipe_tag_codes": s.allowed_recipe_tag_codes,
                "excluded_recipe_tag_codes": s.excluded_recipe_tag_codes,
                "target_energy_share_min": s.target_energy_share_min,
                "target_energy_share_max": s.target_energy_share_max,
                "minimum_protein_g": s.minimum_protein_g,
                "maximum_preparation_time_minutes": s.maximum_preparation_time_minutes,
                "portion_minimum": s.portion_minimum,
                "portion_maximum": s.portion_maximum,
                "portion_step": s.portion_step,
            }
            for s in x.slots
        ],
    }


def create(session: Session, owner: UUID, payload: PreferencesWrite) -> dict[str, Any]:
    if payload.is_default:
        session.execute(
            update(AutomationPreferences)
            .where(AutomationPreferences.owner_profile_id == owner)
            .values(is_default=False)
        )
    x = AutomationPreferences(
        owner_profile_id=owner,
        **{
            k: (
                [str(v) for v in val]
                if k == "excluded_recipe_ids"
                else {a: str(b) for a, b in val.items()}
                if k == "scoring_weights"
                else val
            )
            for k, val in payload.model_dump(exclude={"slots"}).items()
        },
    )
    session.add(x)
    session.flush()
    slots = payload.slots or [
        SlotWrite(slot_code=c, meal_type=c, position=i)
        for i, c in enumerate(("breakfast", "lunch", "dinner"))
    ]
    for s in slots:
        session.add(AutomationMealSlot(automation_preferences_id=x.id, **s.model_dump()))
    session.commit()
    return serialize(get(session, owner, x.id))


def replace(session: Session, owner: UUID, pid: UUID, payload: PreferencesWrite) -> dict[str, Any]:
    x = get(session, owner, pid)
    if payload.is_default:
        session.execute(
            update(AutomationPreferences)
            .where(
                AutomationPreferences.owner_profile_id == owner,
                AutomationPreferences.id != pid,
            )
            .values(is_default=False)
        )
    values = payload.model_dump(exclude={"slots"})
    for key, value in values.items():
        if key == "excluded_recipe_ids":
            value = [str(item) for item in value]
        elif key == "scoring_weights":
            value = {code: str(weight) for code, weight in value.items()}
        setattr(x, key, value)
    x.slots.clear()
    session.flush()
    slots = payload.slots or [
        SlotWrite(slot_code=code, meal_type=code, position=position)
        for position, code in enumerate(("breakfast", "lunch", "dinner"))
    ]
    x.slots.extend(
        AutomationMealSlot(automation_preferences_id=x.id, **slot.model_dump()) for slot in slots
    )
    session.commit()
    return serialize(get(session, owner, pid))


def list_all(session: Session, owner: UUID, archived: bool = False) -> list[dict[str, Any]]:
    return [
        serialize(x)
        for x in session.scalars(
            select(AutomationPreferences)
            .where(
                AutomationPreferences.owner_profile_id == owner,
                AutomationPreferences.is_archived.is_(archived),
            )
            .options(selectinload(AutomationPreferences.slots))
            .order_by(AutomationPreferences.name)
        )
    ]


def archive(session: Session, owner: UUID, pid: UUID, restore: bool = False) -> dict[str, Any]:
    x = get(session, owner, pid)
    x.is_archived = not restore
    x.archived_at = None if restore else datetime.now(UTC)
    session.commit()
    return serialize(x)


def applications(session: Session, owner: UUID) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "scope": item.scope,
            "date_from": item.date_from,
            "date_to": item.date_to,
            "automation_preferences_id": item.automation_preferences_id,
            "assessment_ids": item.assessment_ids,
            "applied_references": item.applied_references,
            "applied_slot_count": item.applied_slot_count,
            "client_operation_id": item.client_operation_id,
            "created_at": item.created_at,
        }
        for item in session.scalars(
            select(AutomationApplication)
            .where(AutomationApplication.owner_profile_id == owner)
            .order_by(AutomationApplication.created_at.desc())
        )
    ]
