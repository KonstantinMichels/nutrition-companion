from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.foods import repository as food_repository
from app.modules.foods import service as food_service
from app.modules.recipes import repository
from app.modules.recipes.engine.calculation import calculate_recipe, scale_servings
from app.modules.recipes.enums import RECIPE_TAGS
from app.modules.recipes.models import Recipe, RecipeIngredient, RecipeStep
from app.modules.recipes.schemas import (
    IngredientResponse,
    RecipeResponse,
    RecipeWrite,
    StepResponse,
)

UNIT_NAMES_DE = {
    "g": "g",
    "ml": "ml",
    "piece": "Stück",
    "serving": "Portion",
    "slice": "Scheibe",
    "teaspoon": "Teelöffel",
    "tablespoon": "Esslöffel",
}


def error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def require(session: Session, profile_id: UUID, recipe_id: UUID) -> Recipe:
    recipe = repository.get(session, profile_id, recipe_id)
    if recipe is None:
        raise error("RECIPE_NOT_FOUND", "Das Rezept wurde nicht gefunden.", 404)
    return recipe


def _normalize(session: Session, profile_id: UUID, payload: RecipeWrite, recipe: Recipe) -> None:
    recipe.ingredients.clear()
    for position, item in enumerate(payload.ingredients, 1):
        food = food_repository.get_food(session, profile_id, item.food_id)
        if food is None:
            raise error(
                "INGREDIENT_FOOD_NOT_FOUND",
                "Ein ausgewähltes Lebensmittel wurde nicht gefunden.",
                404,
            )
        if food.is_archived:
            raise error(
                "INGREDIENT_FOOD_ARCHIVED",
                "Archivierte Lebensmittel können nicht neu hinzugefügt werden.",
                409,
            )
        measure = None
        estimated = False
        if item.unit_type == "measure":
            measure = next((m for m in food.measures if m.id == item.food_measure_id), None)
            if measure is None:
                raise error(
                    "INGREDIENT_MEASURE_INVALID", "Das Haushaltsmaß gehört nicht zum Lebensmittel."
                )
            normalized = food_service.convert_measure_to_base_quantity(
                food, measure.unit_code, item.quantity
            )
            estimated = measure.is_estimated
            source = "food_measure"
        elif item.unit_type == "custom_measure":
            assert item.equivalent_quantity is not None
            assert item.equivalent_unit is not None
            try:
                normalized = food_service.normalize_base_quantity(
                    food,
                    item.quantity * item.equivalent_quantity,
                    item.equivalent_unit,
                )
            except ApiError as exc:
                raise error("INGREDIENT_UNIT_INCOMPATIBLE", exc.message) from exc
            source = "custom_measure"
        else:
            try:
                normalized = food_service.normalize_base_quantity(
                    food, item.quantity, item.unit_code
                )
            except ApiError as exc:
                raise error("INGREDIENT_UNIT_INCOMPATIBLE", exc.message) from exc
            source = "direct" if item.unit_code == food.reference_unit else "density"
        recipe.ingredients.append(
            RecipeIngredient(
                food_id=food.id,
                position=position,
                quantity=item.quantity,
                unit_type=item.unit_type,
                unit_code=item.unit_code,
                food_measure_id=None if measure is None else measure.id,
                normalized_quantity=normalized,
                normalized_unit=food.reference_unit,
                conversion_source=source,
                conversion_is_estimated=estimated,
                preparation_note=item.preparation_note,
                is_optional=item.is_optional,
            )
        )
    recipe.steps.clear()
    for position, step_item in enumerate(payload.steps, 1):
        recipe.steps.append(
            RecipeStep(
                position=position,
                instruction=step_item.instruction,
                optional_duration_minutes=step_item.optional_duration_minutes,
            )
        )


def _metadata(recipe: Recipe, payload: RecipeWrite) -> None:
    recipe.name, recipe.normalized_name = payload.name, payload.name.casefold()
    recipe.description, recipe.servings = payload.description, payload.servings
    recipe.preparation_time_minutes = payload.preparation_time_minutes
    recipe.cooking_time_minutes = payload.cooking_time_minutes
    recipe.resting_time_minutes = payload.resting_time_minutes
    recipe.finished_weight_g, recipe.notes = payload.finished_weight_g, payload.notes
    recipe.source_url = str(payload.source_url) if payload.source_url else None
    recipe.tags = payload.tags


def create(session: Session, profile_id: UUID, payload: RecipeWrite) -> RecipeResponse:
    if (
        repository.duplicates(session, profile_id, payload.name.casefold())
        and not payload.confirm_duplicate
    ):
        raise error(
            "RECIPE_DUPLICATE_WARNING", "Ein Rezept mit diesem Namen ist bereits vorhanden.", 409
        )
    recipe = Recipe(
        owner_profile_id=profile_id,
        name=payload.name,
        normalized_name=payload.name.casefold(),
        servings=payload.servings,
        source_type="user_created",
        tags=[],
    )
    _metadata(recipe, payload)
    _normalize(session, profile_id, payload, recipe)
    try:
        session.add(recipe)
        session.commit()
        return serialize(require(session, profile_id, recipe.id))
    except Exception:
        session.rollback()
        raise


def update(
    session: Session, profile_id: UUID, recipe_id: UUID, payload: RecipeWrite
) -> RecipeResponse:
    recipe = require(session, profile_id, recipe_id)
    if recipe.is_archived:
        raise error("RECIPE_ARCHIVED", "Stelle das Rezept vor dem Bearbeiten wieder her.", 409)
    if (
        repository.duplicates(session, profile_id, payload.name.casefold(), recipe.id)
        and not payload.confirm_duplicate
    ):
        raise error(
            "RECIPE_DUPLICATE_WARNING", "Ein Rezept mit diesem Namen ist bereits vorhanden.", 409
        )
    _metadata(recipe, payload)
    _normalize(session, profile_id, payload, recipe)
    session.commit()
    return serialize(require(session, profile_id, recipe.id))


def duplicate(session: Session, profile_id: UUID, recipe_id: UUID) -> RecipeResponse:
    source = require(session, profile_id, recipe_id)
    copy = Recipe(
        owner_profile_id=profile_id,
        name=f"Kopie von {source.name}",
        normalized_name=f"kopie von {source.name}".casefold(),
        description=source.description,
        servings=source.servings,
        preparation_time_minutes=source.preparation_time_minutes,
        cooking_time_minutes=source.cooking_time_minutes,
        resting_time_minutes=source.resting_time_minutes,
        finished_weight_g=source.finished_weight_g,
        source_type="user_created",
        notes=source.notes,
        tags=list(source.tags),
    )
    for item in source.ingredients:
        copy.ingredients.append(
            RecipeIngredient(
                food_id=item.food_id,
                position=item.position,
                quantity=item.quantity,
                unit_type=item.unit_type,
                unit_code=item.unit_code,
                food_measure_id=item.food_measure_id,
                normalized_quantity=item.normalized_quantity,
                normalized_unit=item.normalized_unit,
                conversion_source=item.conversion_source,
                conversion_is_estimated=item.conversion_is_estimated,
                preparation_note=item.preparation_note,
                is_optional=item.is_optional,
            )
        )
    for step_item in source.steps:
        copy.steps.append(
            RecipeStep(
                position=step_item.position,
                instruction=step_item.instruction,
                optional_duration_minutes=step_item.optional_duration_minutes,
            )
        )
    session.add(copy)
    session.commit()
    return serialize(require(session, profile_id, copy.id))


def archive(session: Session, profile_id: UUID, recipe_id: UUID) -> Recipe:
    recipe = require(session, profile_id, recipe_id)
    recipe.is_archived = True
    recipe.archived_at = datetime.now(UTC)
    session.commit()
    return recipe


def restore(session: Session, profile_id: UUID, recipe_id: UUID) -> RecipeResponse:
    recipe = require(session, profile_id, recipe_id)
    recipe.is_archived = False
    recipe.archived_at = None
    session.commit()
    return serialize(recipe)


def permanently_delete(session: Session, profile_id: UUID, recipe_id: UUID) -> UUID:
    """Permanently delete one owned recipe and its ingredient/step graph."""

    recipe = require(session, profile_id, recipe_id)
    deleted_id = recipe.id
    try:
        session.delete(recipe)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return deleted_id


def scaled(recipe: Recipe, desired: Decimal) -> dict[str, object]:
    if desired <= 0:
        raise error("INVALID_SERVING_COUNT", "Die Portionszahl muss größer als null sein.")
    return scale_servings(recipe, desired)


def serialize(recipe: Recipe) -> RecipeResponse:
    calculation = calculate_recipe(recipe)
    ingredients = [
        IngredientResponse(
            id=i.id,
            position=i.position,
            food_id=i.food_id,
            food_name=i.food.name,
            food_brand=i.food.brand,
            food_is_archived=i.food.is_archived,
            quantity=i.quantity,
            unit_type=i.unit_type,
            unit_code=i.unit_code,
            unit_name=i.food_measure.name
            if i.food_measure
            else UNIT_NAMES_DE.get(i.unit_code, i.unit_code),
            food_measure_id=i.food_measure_id,
            equivalent_quantity=(
                i.food_measure.equivalent_quantity / i.food_measure.quantity
                if i.food_measure
                else i.normalized_quantity / i.quantity
                if i.unit_type == "custom_measure"
                else None
            ),
            equivalent_unit=(
                i.food_measure.equivalent_unit
                if i.food_measure
                else i.normalized_unit
                if i.unit_type == "custom_measure"
                else None
            ),
            normalized_quantity=i.normalized_quantity,
            normalized_unit=i.normalized_unit,
            conversion_source=i.conversion_source,
            conversion_is_estimated=i.conversion_is_estimated,
            preparation_note=i.preparation_note,
            is_optional=i.is_optional,
        )
        for i in recipe.ingredients
    ]
    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        servings=recipe.servings,
        preparation_time_minutes=recipe.preparation_time_minutes,
        cooking_time_minutes=recipe.cooking_time_minutes,
        resting_time_minutes=recipe.resting_time_minutes,
        finished_weight_g=recipe.finished_weight_g,
        source_type=recipe.source_type,
        source_name=recipe.source_name,
        source_url=recipe.source_url,
        notes=recipe.notes,
        tags=recipe.tags,
        tag_labels=[RECIPE_TAGS[t] for t in recipe.tags],
        is_archived=recipe.is_archived,
        archived_at=recipe.archived_at,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
        ingredients=ingredients,
        steps=[
            StepResponse(
                id=s.id,
                position=s.position,
                instruction=s.instruction,
                optional_duration_minutes=s.optional_duration_minutes,
            )
            for s in recipe.steps
        ],
        **calculation,
    )
