from __future__ import annotations

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.branding import CONSENT_TEXT_VERSION
from app.core.errors import ApiError
from app.modules.daily_meal_planning.models import DailyMealPlan, Meal
from app.modules.foods.models import Food
from app.modules.foods.nutrient_catalog import NUTRIENT_BY_CODE
from app.modules.meal_plan_automation.models import (
    AutomationApplication,
    AutomationPreferences,
)
from app.modules.nutrition_assessment.models import Assessment
from app.modules.pantry.models import PantryLocation, PantryMovement, PantryStockLot
from app.modules.pantry_aware_shopping.models import PantryAwareShoppingOperation
from app.modules.privacy import repository
from app.modules.privacy.models import (
    ConsentRecord,
    DeletionRecord,
    PrivacyAction,
    ProcessingPurpose,
)
from app.modules.privacy.schemas import ConsentCreate, DeletionResponse, PrivacyExportResponse
from app.modules.profiles import repository as profile_repository
from app.modules.profiles.models import (
    ActivityProfile,
    DietaryRestriction,
    HealthScreening,
    Measurement,
    NutritionGoal,
)
from app.modules.purchase_to_pantry.models import (
    PurchaseToPantryHandoff,
    PurchaseToPantryHandoffItem,
)
from app.modules.recipes.models import Recipe, RecipeIngredient
from app.modules.shopping_lists.models import ShoppingList, ShoppingListItem

REQUIRED_ASSESSMENT_PURPOSE = "nutrition_assessment_calculation"


def grant_consent(session: Session, profile_id: UUID, payload: ConsentCreate) -> ConsentRecord:
    if profile_repository.get_profile(session, profile_id) is None:
        raise ApiError(
            code="PROFILE_NOT_FOUND",
            message="Speichere zuerst dein Profil.",
            status_code=404,
        )
    if not payload.affirmed:
        raise ApiError(
            code="CONSENT_NOT_GRANTED",
            message="Ohne ausdrückliche Einwilligung wird keine Auswertung erstellt.",
            status_code=422,
        )
    if payload.consent_text_version != CONSENT_TEXT_VERSION:
        raise ApiError(
            code="CONSENT_TEXT_VERSION_MISMATCH",
            message="Die Einwilligungsinformation wurde aktualisiert. Bitte lies sie erneut.",
            status_code=409,
        )
    purpose = session.get(ProcessingPurpose, payload.purpose_code)
    if purpose is None or not purpose.consent_required:
        raise ApiError(
            code="PURPOSE_NOT_AVAILABLE",
            message="Der Verarbeitungszweck ist nicht verfügbar.",
            status_code=409,
        )

    existing = repository.active_consent(
        session,
        profile_id,
        payload.purpose_code,
        payload.consent_text_version,
    )
    if existing is not None:
        return existing

    now = datetime.now(UTC)
    record = ConsentRecord(
        profile_id=profile_id,
        purpose_code=payload.purpose_code,
        consent_text_version=payload.consent_text_version,
        status="granted",
        granted_at=now,
        source=payload.source,
    )
    session.add(record)
    session.add(PrivacyAction(profile_id=profile_id, action_type="consent_granted"))
    session.commit()
    return record


def withdraw_consent(session: Session, profile_id: UUID, consent_id: UUID) -> ConsentRecord:
    record = session.get(ConsentRecord, consent_id)
    if record is None or record.profile_id != profile_id:
        raise ApiError(
            code="CONSENT_NOT_FOUND",
            message="Der Einwilligungsnachweis wurde nicht gefunden.",
            status_code=404,
        )
    active_records = repository.active_consents_for_version(
        session,
        profile_id,
        record.purpose_code,
        record.consent_text_version,
    )
    if active_records:
        withdrawn_at = datetime.now(UTC)
        for active_record in active_records:
            active_record.status = "withdrawn"
            active_record.withdrawn_at = withdrawn_at
        session.add(PrivacyAction(profile_id=profile_id, action_type="consent_withdrawn"))
        session.commit()
    return record


def require_assessment_consent(session: Session, profile_id: UUID) -> ConsentRecord:
    consent = repository.active_consent(
        session,
        profile_id,
        REQUIRED_ASSESSMENT_PURPOSE,
        CONSENT_TEXT_VERSION,
    )
    if consent is None:
        raise ApiError(
            code="CONSENT_REQUIRED",
            message="Für eine neue Auswertung ist deine ausdrückliche Einwilligung erforderlich.",
            status_code=403,
        )
    return consent


def _measurement_dict(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "measurement_type": item.measurement_type,
        "value": item.value,
        "unit": item.unit,
        "measured_at": item.measured_at,
        "source_type": item.source_type,
        "created_at": item.created_at,
    }


def build_export(session: Session, profile_id: UUID) -> PrivacyExportResponse:
    profile = profile_repository.get_profile(session, profile_id)
    if profile is None:
        raise ApiError(
            code="PROFILE_NOT_FOUND",
            message="Es sind keine Profildaten zum Exportieren gespeichert.",
            status_code=404,
        )
    assessments = list(
        session.scalars(
            select(Assessment)
            .where(Assessment.profile_id == profile_id)
            .options(selectinload(Assessment.metrics), selectinload(Assessment.safety_flags))
            .order_by(Assessment.calculated_at)
        )
    )
    consents = repository.list_consents(session, profile_id)
    foods = list(
        session.scalars(
            select(Food)
            .where(Food.owner_profile_id == profile_id)
            .options(selectinload(Food.nutrients), selectinload(Food.measures))
            .order_by(Food.created_at)
        )
    )
    recipes = list(
        session.scalars(
            select(Recipe)
            .where(Recipe.owner_profile_id == profile_id)
            .options(
                selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food),
                selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_measure),
                selectinload(Recipe.steps),
            )
            .order_by(Recipe.created_at)
        )
    )
    daily_plans = list(
        session.scalars(
            select(DailyMealPlan)
            .where(DailyMealPlan.owner_profile_id == profile_id)
            .options(selectinload(DailyMealPlan.meals).selectinload(Meal.entries))
            .order_by(DailyMealPlan.plan_date, DailyMealPlan.created_at)
        )
    )
    pantry_locations = list(
        session.scalars(
            select(PantryLocation)
            .where(PantryLocation.owner_profile_id == profile_id)
            .order_by(PantryLocation.position)
        )
    )
    pantry_lots = list(
        session.scalars(
            select(PantryStockLot)
            .where(PantryStockLot.owner_profile_id == profile_id)
            .order_by(PantryStockLot.created_at)
        )
    )
    pantry_movements = list(
        session.scalars(
            select(PantryMovement)
            .where(PantryMovement.owner_profile_id == profile_id)
            .order_by(PantryMovement.created_at)
        )
    )
    shopping_lists = list(
        session.scalars(
            select(ShoppingList)
            .where(ShoppingList.owner_profile_id == profile_id)
            .options(selectinload(ShoppingList.items).selectinload(ShoppingListItem.sources))
            .order_by(ShoppingList.created_at)
        )
    )
    purchase_handoffs = list(
        session.scalars(
            select(PurchaseToPantryHandoff)
            .where(PurchaseToPantryHandoff.owner_profile_id == profile_id)
            .options(
                selectinload(PurchaseToPantryHandoff.items).selectinload(
                    PurchaseToPantryHandoffItem.destinations
                )
            )
            .order_by(PurchaseToPantryHandoff.created_at)
        )
    )
    pantry_aware_operations = list(
        session.scalars(
            select(PantryAwareShoppingOperation)
            .where(PantryAwareShoppingOperation.owner_profile_id == profile_id)
            .order_by(PantryAwareShoppingOperation.created_at)
        )
    )
    automation_preferences = list(
        session.scalars(
            select(AutomationPreferences)
            .where(AutomationPreferences.owner_profile_id == profile_id)
            .options(selectinload(AutomationPreferences.slots))
            .order_by(AutomationPreferences.created_at)
        )
    )
    automation_applications = list(
        session.scalars(
            select(AutomationApplication)
            .where(AutomationApplication.owner_profile_id == profile_id)
            .order_by(AutomationApplication.created_at)
        )
    )
    session.add(PrivacyAction(profile_id=profile_id, action_type="export_requested"))
    session.flush()
    privacy_actions = list(
        session.scalars(
            select(PrivacyAction)
            .where(PrivacyAction.profile_id == profile_id)
            .order_by(PrivacyAction.occurred_at)
        )
    )
    activity = profile.activity_profile
    goal = profile.goal
    screening = profile.health_screening

    export_data: dict[str, Any] = {
        "profile": {
            "id": profile.id,
            "birth_date": profile.birth_date,
            "physiological_category": profile.physiological_category,
            "height_cm": profile.height_cm,
            "current_weight_kg": profile.current_weight_kg,
            "dietary_preference": profile.dietary_preference,
            "preferred_meals_per_day": profile.preferred_meals_per_day,
            "preferred_meal_timing": profile.preferred_meal_timing,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        },
        "measurements": [_measurement_dict(item) for item in profile.measurements],
        "activity": None
        if activity is None
        else {
            "occupational_activity_category": activity.occupational_activity_category,
            "average_daily_steps": activity.average_daily_steps,
            "active_commuting": activity.active_commuting,
            "movement_notes": activity.movement_notes,
            "manual_pal_override": activity.manual_pal_override,
            "sports": [
                {
                    "id": sport.id,
                    "sport_type": sport.sport_type,
                    "sessions_per_week": sport.sessions_per_week,
                    "minutes_per_session": sport.minutes_per_session,
                    "intensity": sport.intensity,
                    "note": sport.note,
                }
                for sport in activity.sports
            ],
            "created_at": activity.created_at,
            "updated_at": activity.updated_at,
        },
        "goal": None
        if goal is None
        else {
            "goal_type": goal.goal_type,
            "target_weight_kg": goal.target_weight_kg,
            "desired_intensity": goal.desired_intensity,
            "requested_weekly_rate_kg": goal.requested_weekly_rate_kg,
            "created_at": goal.created_at,
            "updated_at": goal.updated_at,
        },
        "dietary_restrictions": [
            {
                "id": item.id,
                "restriction_type": item.restriction_type,
                "value": item.value,
                "hard_exclusion": item.hard_exclusion,
                "note": item.note,
            }
            for item in profile.restrictions
        ],
        "health_screening": None
        if screening is None
        else {
            "pregnant": screening.pregnant,
            "breastfeeding": screening.breastfeeding,
            "diagnosed_eating_disorder": screening.diagnosed_eating_disorder,
            "diabetes": screening.diabetes,
            "kidney_disease": screening.kidney_disease,
            "liver_disease": screening.liver_disease,
            "medically_prescribed_diet": screening.medically_prescribed_diet,
            "serious_metabolic_condition": screening.serious_metabolic_condition,
            "other_professional_nutrition_condition": (
                screening.other_professional_nutrition_condition
            ),
            "user_note": screening.user_note,
            "screened_at": screening.screened_at,
        },
        "consent_records": [
            {
                "id": item.id,
                "purpose_code": item.purpose_code,
                "consent_text_version": item.consent_text_version,
                "status": item.status,
                "granted_at": item.granted_at,
                "withdrawn_at": item.withdrawn_at,
                "source": item.source,
                "created_at": item.created_at,
            }
            for item in consents
        ],
        "privacy_actions": [
            {
                "action_type": item.action_type,
                "occurred_at": item.occurred_at,
                "outcome": item.outcome,
            }
            for item in privacy_actions
        ],
        "assessments": [
            {
                "id": assessment.id,
                "client_request_id": assessment.client_request_id,
                "input_snapshot": assessment.input_snapshot,
                "supported_scope_status": assessment.supported_scope_status,
                "reference_set_identifier": assessment.reference_set_identifier,
                "reference_set_version": assessment.reference_set_version,
                "application_rule_set_identifier": assessment.application_rule_set_identifier,
                "application_rule_set_version": assessment.application_rule_set_version,
                "engine_version": assessment.engine_version,
                "calculated_at": assessment.calculated_at,
                "summary": assessment.summary,
                "metrics": [
                    {
                        "metric_code": metric.metric_code,
                        "raw_value": metric.raw_value,
                        "display_value": metric.display_value,
                        "lower_value": metric.lower_value,
                        "upper_value": metric.upper_value,
                        "unit": metric.unit,
                        "method_code": metric.method_code,
                        "explanation_de": metric.explanation_de,
                        "limitations_de": metric.limitations_de,
                        "calculation_inputs": metric.calculation_inputs,
                        "source_metadata": metric.source_metadata,
                        "application_rule_identifier": metric.application_rule_identifier,
                        "confidence_type": metric.confidence_type,
                    }
                    for metric in assessment.metrics
                ],
                "safety_flags": [
                    {
                        "code": flag.code,
                        "severity": flag.severity,
                        "explanation_de": flag.explanation_de,
                        "recommended_action_de": flag.recommended_action_de,
                    }
                    for flag in assessment.safety_flags
                ],
            }
            for assessment in assessments
        ],
        "user_created_foods": [
            {
                "id": food.id,
                "name": food.name,
                "brand": food.brand,
                "description": food.description,
                "category_code": food.category_code,
                "reference_quantity": food.reference_quantity,
                "reference_unit": food.reference_unit,
                "density_g_per_ml": food.density_g_per_ml,
                "source_type": food.source_type,
                "is_archived": food.is_archived,
                "archived_at": food.archived_at,
                "created_at": food.created_at,
                "updated_at": food.updated_at,
                "nutrients": [
                    {
                        "code": nutrient.nutrient_code,
                        "name_de": NUTRIENT_BY_CODE[nutrient.nutrient_code].display_name_de,
                        "amount": nutrient.amount,
                        "unit": nutrient.unit,
                        "value_source": nutrient.value_source,
                        "is_estimated": nutrient.is_estimated,
                    }
                    for nutrient in food.nutrients
                ],
                "measures": [
                    {
                        "name": measure.name,
                        "quantity": measure.quantity,
                        "unit_code": measure.unit_code,
                        "equivalent_quantity": measure.equivalent_quantity,
                        "equivalent_unit": measure.equivalent_unit,
                        "is_estimated": measure.is_estimated,
                        "source_type": measure.source_type,
                    }
                    for measure in food.measures
                ],
            }
            for food in foods
        ],
        "recipes": [
            {
                "id": recipe.id,
                "name": recipe.name,
                "description": recipe.description,
                "servings": recipe.servings,
                "preparation_time_minutes": recipe.preparation_time_minutes,
                "cooking_time_minutes": recipe.cooking_time_minutes,
                "resting_time_minutes": recipe.resting_time_minutes,
                "finished_weight_g": recipe.finished_weight_g,
                "source_type": recipe.source_type,
                "source_name": recipe.source_name,
                "source_url": recipe.source_url,
                "notes": recipe.notes,
                "tags": recipe.tags,
                "is_archived": recipe.is_archived,
                "archived_at": recipe.archived_at,
                "created_at": recipe.created_at,
                "updated_at": recipe.updated_at,
                "ingredients": [
                    {
                        "food_id": item.food_id,
                        "food_name": item.food.name,
                        "position": item.position,
                        "quantity": item.quantity,
                        "unit_code": item.unit_code,
                        "food_measure_id": item.food_measure_id,
                        "normalized_quantity": item.normalized_quantity,
                        "normalized_unit": item.normalized_unit,
                        "preparation_note": item.preparation_note,
                        "is_optional": item.is_optional,
                    }
                    for item in recipe.ingredients
                ],
                "steps": [
                    {
                        "position": step.position,
                        "instruction": step.instruction,
                        "optional_duration_minutes": step.optional_duration_minutes,
                    }
                    for step in recipe.steps
                ],
            }
            for recipe in recipes
        ],
        "daily_meal_plans": [
            {
                "id": plan.id,
                "plan_date": plan.plan_date,
                "assessment_id": plan.assessment_id,
                "name": plan.name,
                "notes": plan.notes,
                "is_archived": plan.is_archived,
                "archived_at": plan.archived_at,
                "created_at": plan.created_at,
                "updated_at": plan.updated_at,
                "meals": [
                    {
                        "id": meal.id,
                        "meal_type": meal.meal_type,
                        "custom_name": meal.custom_name,
                        "planned_time": meal.planned_time,
                        "position": meal.position,
                        "notes": meal.notes,
                        "created_at": meal.created_at,
                        "updated_at": meal.updated_at,
                        "entries": [
                            {
                                "id": entry.id,
                                "entry_type": entry.entry_type,
                                "recipe_id": entry.recipe_id,
                                "food_id": entry.food_id,
                                "recipe_portion_count": entry.recipe_portion_count,
                                "food_quantity": entry.food_quantity,
                                "food_unit_code": entry.food_unit_code,
                                "food_measure_id": entry.food_measure_id,
                                "position": entry.position,
                                "note": entry.note,
                                "created_at": entry.created_at,
                                "updated_at": entry.updated_at,
                            }
                            for entry in meal.entries
                        ],
                    }
                    for meal in plan.meals
                ],
            }
            for plan in daily_plans
        ],
        "meal_plan_automation_preferences": [
            {
                "id": item.id,
                "name": item.name,
                "is_default": item.is_default,
                "assessment_selection_mode": item.assessment_selection_mode,
                "selected_assessment_id": item.selected_assessment_id,
                "generation_scope_default": item.generation_scope_default,
                "pantry_preference": item.pantry_preference,
                "shopping_effort_preference": item.shopping_effort_preference,
                "maximum_recipe_repetitions_per_week": (item.maximum_recipe_repetitions_per_week),
                "minimum_days_between_same_recipe": item.minimum_days_between_same_recipe,
                "maximum_preparation_time_minutes": item.maximum_preparation_time_minutes,
                "scoring_weights": item.scoring_weights,
                "optimizer_enabled": item.optimizer_enabled,
                "default_generation_engine": item.default_generation_engine,
                "solver_time_limit_day_seconds": item.solver_time_limit_day_seconds,
                "solver_time_limit_week_seconds": item.solver_time_limit_week_seconds,
                "solver_relative_gap_limit": item.solver_relative_gap_limit,
                "solver_candidate_limit_per_slot": item.solver_candidate_limit_per_slot,
                "maximum_recipe_repetitions_per_day": (item.maximum_recipe_repetitions_per_day),
                "strict_energy_target": item.strict_energy_target,
                "strict_protein_minimum": item.strict_protein_minimum,
                "strict_fiber_minimum": item.strict_fiber_minimum,
                "strict_fat_range": item.strict_fat_range,
                "strict_saturated_fat_maximum": item.strict_saturated_fat_maximum,
                "strict_daily_preparation_time": item.strict_daily_preparation_time,
                "maximum_daily_preparation_time_minutes": (
                    item.maximum_daily_preparation_time_minutes
                ),
                "maximum_weekly_unique_shopping_items": (item.maximum_weekly_unique_shopping_items),
                "constraint_relaxation_enabled": item.constraint_relaxation_enabled,
                "relaxable_constraint_priorities": item.relaxable_constraint_priorities,
                "objective_weights": item.objective_weights,
                "meal_prep_preference": item.meal_prep_preference,
                "compare_with_greedy": item.compare_with_greedy,
                "is_archived": item.is_archived,
                "slots": [
                    {
                        "slot_code": slot.slot_code,
                        "meal_type": slot.meal_type,
                        "default_time": slot.default_time,
                        "is_enabled": slot.is_enabled,
                        "portion_minimum": slot.portion_minimum,
                        "portion_maximum": slot.portion_maximum,
                        "portion_step": slot.portion_step,
                    }
                    for slot in item.slots
                ],
            }
            for item in automation_preferences
        ],
        "meal_plan_automation_applications": [
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
                "generation_engine": item.generation_engine,
                "solver_status": item.solver_status,
                "solver_version": item.solver_version,
                "objective_value": item.objective_value,
                "relative_gap": item.relative_gap,
                "relaxation_used": item.relaxation_used,
                "relaxation_summary": item.relaxation_summary,
                "objective_summary": item.objective_summary,
                "greedy_comparison_enabled": item.greedy_comparison_enabled,
                "created_at": item.created_at,
            }
            for item in automation_applications
        ],
        "pantry_locations": [
            {
                "id": item.id,
                "name": item.name,
                "location_type": item.location_type,
                "position": item.position,
                "description": item.description,
                "is_archived": item.is_archived,
                "archived_at": item.archived_at,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in pantry_locations
        ],
        "pantry_stock_lots": [
            {
                "id": item.id,
                "food_id": item.food_id,
                "location_id": item.location_id,
                "current_quantity": item.current_quantity,
                "normalized_unit": item.normalized_unit,
                "initial_entered_quantity": item.initial_entered_quantity,
                "initial_entered_unit_code": item.initial_entered_unit_code,
                "initial_food_measure_id": item.initial_food_measure_id,
                "initial_conversion_estimated": item.initial_conversion_estimated,
                "purchase_date": item.purchase_date,
                "opened_date": item.opened_date,
                "best_before_date": item.best_before_date,
                "use_by_date": item.use_by_date,
                "note": item.note,
                "is_depleted": item.is_depleted,
                "depleted_at": item.depleted_at,
                "is_archived": item.is_archived,
                "archived_at": item.archived_at,
                "version": item.version,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in pantry_lots
        ],
        "pantry_movements": [
            {
                "id": item.id,
                "stock_lot_id": item.stock_lot_id,
                "movement_type": item.movement_type,
                "quantity_delta": item.quantity_delta,
                "normalized_unit": item.normalized_unit,
                "balance_before": item.balance_before,
                "balance_after": item.balance_after,
                "entered_quantity": item.entered_quantity,
                "entered_unit_code": item.entered_unit_code,
                "food_measure_id": item.food_measure_id,
                "conversion_estimated": item.conversion_estimated,
                "source_type": item.source_type,
                "note": item.note,
                "target_location_id": item.target_location_id,
                "related_stock_lot_id": item.related_stock_lot_id,
                "client_operation_id": item.client_operation_id,
                "created_at": item.created_at,
            }
            for item in pantry_movements
        ],
        "shopping_lists": [
            {
                "id": shopping.id,
                "name": shopping.name,
                "source_type": shopping.source_type,
                "source_daily_plan_id": shopping.source_daily_plan_id,
                "source_week_start": shopping.source_week_start,
                "source_week_end": shopping.source_week_end,
                "pantry_considered": shopping.pantry_considered,
                "status": shopping.status,
                "is_archived": shopping.is_archived,
                "notes": shopping.notes,
                "version": shopping.version,
                "items": [
                    {
                        "id": item.id,
                        "item_type": item.item_type,
                        "origin_type": item.origin_type,
                        "food_id": item.food_id,
                        "food_name_snapshot": item.food_name_snapshot,
                        "manual_name": item.manual_name,
                        "category_code": item.category_code,
                        "required_quantity": item.required_quantity,
                        "pantry_available_quantity": item.pantry_available_quantity,
                        "suggested_purchase_quantity": item.suggested_purchase_quantity,
                        "purchase_quantity": item.purchase_quantity,
                        "manual_quantity": item.manual_quantity,
                        "manual_unit_label": item.manual_unit_label,
                        "quantity_overridden": item.quantity_overridden,
                        "is_checked": item.is_checked,
                        "note": item.note,
                        "sources": [
                            {
                                "plan_date": source.plan_date,
                                "meal_name": source.meal_name_snapshot,
                                "recipe_name": source.recipe_name_snapshot,
                                "food_id": source.food_id,
                                "source_identity": source.source_identity,
                                "source_version": source.source_version,
                                "pantry_aware_operation_id": source.pantry_aware_operation_id,
                                "quantity": source.quantity,
                                "unit": source.unit,
                                "refreshed_at": source.refreshed_at,
                            }
                            for source in item.sources
                        ],
                    }
                    for item in shopping.items
                ],
            }
            for shopping in shopping_lists
        ],
        "purchase_to_pantry_handoffs": [
            {
                "id": handoff.id,
                "shopping_list_id": handoff.shopping_list_id,
                "shopping_list_name": handoff.shopping_list_name_snapshot,
                "status": handoff.status,
                "completed_at": handoff.completed_at,
                "items": [
                    {
                        "shopping_list_item_id": item.shopping_list_item_id,
                        "shopping_item_name": item.shopping_item_name_snapshot,
                        "food_id": item.food_id,
                        "planned_purchase_quantity": item.planned_purchase_quantity,
                        "planned_purchase_unit": item.planned_purchase_unit,
                        "actual_transferred_quantity": item.actual_transferred_quantity,
                        "canonical_unit": item.canonical_unit,
                        "marked_completed": item.mark_item_handoff_completed,
                        "destinations": [
                            {
                                "destination_type": destination.destination_type,
                                "pantry_location_id": destination.pantry_location_id,
                                "target_stock_lot_id": destination.target_stock_lot_id,
                                "created_stock_lot_id": destination.created_stock_lot_id,
                                "pantry_movement_id": destination.pantry_movement_id,
                                "entered_quantity": destination.entered_quantity,
                                "entered_unit_code": destination.entered_unit_code,
                                "normalized_quantity": destination.normalized_quantity,
                                "normalized_unit": destination.normalized_unit,
                                "purchase_date": destination.purchase_date,
                                "opened_date": destination.opened_date,
                                "best_before_date": destination.best_before_date,
                                "use_by_date": destination.use_by_date,
                                "note": destination.note,
                            }
                            for destination in item.destinations
                        ],
                    }
                    for item in handoff.items
                ],
            }
            for handoff in purchase_handoffs
        ],
        "pantry_aware_shopping_operations": [
            {
                "id": operation.id,
                "target_shopping_list_id": operation.target_shopping_list_id,
                "source_scope_type": operation.source_scope_type,
                "source_reference": operation.source_reference,
                "source_version": operation.source_version,
                "pantry_date_mode": operation.pantry_date_mode,
                "other_open_lists_considered": operation.other_open_lists_considered,
                "client_operation_id": operation.client_operation_id,
                "result_summary": operation.result_summary,
                "applied_at": operation.applied_at,
                "created_at": operation.created_at,
            }
            for operation in pantry_aware_operations
        ],
    }
    session.commit()
    return PrivacyExportResponse(
        generated_at=datetime.now(UTC),
        notice_de=(
            "Dieser Export wurde auf deine ausdrückliche Aktion erstellt und enthält die "
            "im lokalen MVP gespeicherten Profildaten."
        ),
        data=jsonable_encoder(export_data, custom_encoder={Decimal: str}),
    )


def delete_assessment_history(session: Session, profile_id: UUID) -> DeletionResponse:
    if profile_repository.get_profile(session, profile_id) is None:
        raise ApiError(
            code="PROFILE_NOT_FOUND",
            message="Es wurde kein Profil gefunden.",
            status_code=404,
        )
    assessments = list(
        session.scalars(select(Assessment).where(Assessment.profile_id == profile_id))
    )
    count = len(assessments)
    confirmation = secrets.token_hex(8)
    try:
        for assessment in assessments:
            session.delete(assessment)
        session.add(PrivacyAction(profile_id=profile_id, action_type="assessment_history_deleted"))
        session.add(
            DeletionRecord(
                deletion_scope="assessment_history",
                deleted_record_count=count,
                confirmation_code=confirmation,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return DeletionResponse(
        deleted=True,
        scope="assessment_history",
        confirmation_code=confirmation,
        message_de="Der Auswertungsverlauf wurde dauerhaft aus der aktiven Datenbank gelöscht.",
    )


def delete_complete_profile(session: Session, profile_id: UUID) -> DeletionResponse:
    profile = profile_repository.get_profile_record(session, profile_id)
    if profile is None:
        raise ApiError(
            code="PROFILE_NOT_FOUND",
            message="Es wurde kein Profil gefunden.",
            status_code=404,
        )
    assessment_count = session.scalar(
        select(func.count()).select_from(Assessment).where(Assessment.profile_id == profile_id)
    )
    food_count = session.scalar(
        select(func.count()).select_from(Food).where(Food.owner_profile_id == profile_id)
    )
    recipe_count = session.scalar(
        select(func.count()).select_from(Recipe).where(Recipe.owner_profile_id == profile_id)
    )
    daily_plan_count = session.scalar(
        select(func.count())
        .select_from(DailyMealPlan)
        .where(DailyMealPlan.owner_profile_id == profile_id)
    )
    pantry_count = session.scalar(
        select(func.count())
        .select_from(PantryStockLot)
        .where(PantryStockLot.owner_profile_id == profile_id)
    )
    shopping_count = session.scalar(
        select(func.count())
        .select_from(ShoppingList)
        .where(ShoppingList.owner_profile_id == profile_id)
    )
    handoff_count = session.scalar(
        select(func.count())
        .select_from(PurchaseToPantryHandoff)
        .where(PurchaseToPantryHandoff.owner_profile_id == profile_id)
    )
    pantry_aware_count = session.scalar(
        select(func.count())
        .select_from(PantryAwareShoppingOperation)
        .where(PantryAwareShoppingOperation.owner_profile_id == profile_id)
    )
    automation_count = session.scalar(
        select(func.count())
        .select_from(AutomationPreferences)
        .where(AutomationPreferences.owner_profile_id == profile_id)
    )
    approximate_count = (
        1
        + len(profile.measurements)
        + len(profile.restrictions)
        + len(profile.consent_records)
        + int(assessment_count or 0)
        + int(food_count or 0)
        + int(recipe_count or 0)
        + int(daily_plan_count or 0)
        + int(pantry_count or 0)
        + int(shopping_count or 0)
        + int(handoff_count or 0)
        + int(pantry_aware_count or 0)
        + int(automation_count or 0)
        + (1 if profile.activity_profile else 0)
        + (1 if profile.goal else 0)
        + (1 if profile.health_screening else 0)
    )
    confirmation = secrets.token_hex(8)
    try:
        session.execute(
            delete(AutomationApplication).where(
                AutomationApplication.owner_profile_id == profile_id
            )
        )
        session.execute(
            delete(AutomationPreferences).where(
                AutomationPreferences.owner_profile_id == profile_id
            )
        )
        session.flush()
        # Handoff links protect shopping and Pantry records, so remove them first.
        session.execute(
            delete(PantryAwareShoppingOperation).where(
                PantryAwareShoppingOperation.owner_profile_id == profile_id
            )
        )
        session.flush()
        session.execute(
            delete(PurchaseToPantryHandoff).where(
                PurchaseToPantryHandoff.owner_profile_id == profile_id
            )
        )
        session.flush()
        # Shopping snapshots protect plans, recipes and foods, so remove them first.
        session.execute(delete(ShoppingList).where(ShoppingList.owner_profile_id == profile_id))
        session.flush()
        # Plan entries and recipe ingredients protect their source records.
        session.execute(delete(DailyMealPlan).where(DailyMealPlan.owner_profile_id == profile_id))
        session.flush()
        session.execute(delete(PantryMovement).where(PantryMovement.owner_profile_id == profile_id))
        session.execute(delete(PantryStockLot).where(PantryStockLot.owner_profile_id == profile_id))
        session.execute(delete(PantryLocation).where(PantryLocation.owner_profile_id == profile_id))
        session.flush()
        session.execute(delete(Recipe).where(Recipe.owner_profile_id == profile_id))
        session.flush()
        session.execute(delete(Food).where(Food.owner_profile_id == profile_id))
        session.flush()
        session.delete(profile)
        session.flush()
        # Deliberately omit the former profile UUID from post-deletion audit data.
        session.add(PrivacyAction(profile_id=None, action_type="profile_deleted"))
        session.add(
            DeletionRecord(
                deletion_scope="complete_profile",
                deleted_record_count=approximate_count,
                confirmation_code=confirmation,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return DeletionResponse(
        deleted=True,
        scope="complete_profile",
        confirmation_code=confirmation,
        message_de=(
            "Das Profil und die zugehörigen aktiven Daten wurden dauerhaft gelöscht. "
            "Lösche nun auch die lokalen verschlüsselten App-Daten."
        ),
    )


def delete_profile_data_and_assessments(session: Session, profile_id: UUID) -> DeletionResponse:
    profile = profile_repository.get_profile_record(session, profile_id)
    if profile is None or not profile.is_configured:
        raise ApiError(
            code="PROFILE_NOT_FOUND", message="Es wurde kein Profil gefunden.", status_code=404
        )
    confirmation = secrets.token_hex(8)
    try:
        for model in (
            Assessment,
            Measurement,
            DietaryRestriction,
            ActivityProfile,
            NutritionGoal,
            HealthScreening,
        ):
            session.execute(delete(model).where(model.profile_id == profile_id))
        profile.birth_date = datetime(1970, 1, 1, tzinfo=UTC).date()
        profile.physiological_category = "reference_category_a"
        profile.height_cm = Decimal("101")
        profile.current_weight_kg = Decimal("26")
        profile.dietary_preference = "other"
        profile.preferred_meals_per_day = None
        profile.preferred_meal_timing = None
        profile.is_configured = False
        session.add(
            DeletionRecord(
                deletion_scope="profile_and_assessments",
                deleted_record_count=0,
                confirmation_code=confirmation,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return DeletionResponse(
        deleted=True,
        scope="profile_and_assessments",
        confirmation_code=confirmation,
        message_de="Profildaten und Einschätzungen wurden dauerhaft gelöscht.",
    )


def delete_all_recipes(session: Session, profile_id: UUID) -> DeletionResponse:
    from app.modules.daily_meal_planning.models import MealEntry

    plan_reference = session.scalar(
        select(MealEntry.id)
        .join(Meal)
        .join(DailyMealPlan)
        .where(DailyMealPlan.owner_profile_id == profile_id, MealEntry.recipe_id.is_not(None))
        .limit(1)
    )
    if plan_reference is not None:
        raise ApiError(
            code="RECIPES_REFERENCED_BY_DAILY_PLANS",
            message="Tagespläne verwenden noch Rezepte. Entferne zuerst diese Planeinträge.",
            status_code=409,
        )
    confirmation = secrets.token_hex(8)
    count = session.scalar(
        select(func.count()).select_from(Recipe).where(Recipe.owner_profile_id == profile_id)
    )
    session.execute(delete(Recipe).where(Recipe.owner_profile_id == profile_id))
    session.add(
        DeletionRecord(
            deletion_scope="recipes",
            deleted_record_count=int(count or 0),
            confirmation_code=confirmation,
        )
    )
    session.commit()
    return DeletionResponse(
        deleted=True,
        scope="recipes",
        confirmation_code=confirmation,
        message_de="Alle Rezepte wurden dauerhaft gelöscht.",
    )


def delete_all_foods(session: Session, profile_id: UUID) -> DeletionResponse:
    reference_count = session.scalar(
        select(func.count())
        .select_from(RecipeIngredient)
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .where(Recipe.owner_profile_id == profile_id)
    )
    if reference_count:
        raise ApiError(
            code="FOODS_REFERENCED_BY_RECIPES",
            message="Lösche zuerst deine Rezepte, da sie Lebensmittel verwenden.",
            status_code=409,
        )
    from app.modules.daily_meal_planning.models import MealEntry

    plan_reference = session.scalar(
        select(MealEntry.id)
        .join(Meal)
        .join(DailyMealPlan)
        .where(DailyMealPlan.owner_profile_id == profile_id, MealEntry.food_id.is_not(None))
        .limit(1)
    )
    if plan_reference is not None:
        raise ApiError(
            code="FOODS_REFERENCED_BY_DAILY_PLANS",
            message="Tagespläne verwenden noch Lebensmittel. Entferne zuerst diese Planeinträge.",
            status_code=409,
        )
    confirmation = secrets.token_hex(8)
    count = session.scalar(
        select(func.count()).select_from(Food).where(Food.owner_profile_id == profile_id)
    )
    session.execute(delete(Food).where(Food.owner_profile_id == profile_id))
    session.add(
        DeletionRecord(
            deletion_scope="foods",
            deleted_record_count=int(count or 0),
            confirmation_code=confirmation,
        )
    )
    session.commit()
    return DeletionResponse(
        deleted=True,
        scope="foods",
        confirmation_code=confirmation,
        message_de="Alle Lebensmittel wurden dauerhaft gelöscht.",
    )
