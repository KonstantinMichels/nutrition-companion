from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.foods import repository
from app.modules.foods.conversions import kcal_to_kj, salt_to_sodium, sodium_to_salt
from app.modules.foods.models import Food, FoodMeasure, FoodNutrient
from app.modules.foods.nutrient_catalog import CORE_CODES, NUTRIENT_BY_CODE
from app.modules.foods.quality import calculate_quality
from app.modules.foods.schemas import (
    BarcodeImportRequest,
    FoodResponse,
    FoodWrite,
    MeasureResponse,
    NutrientResponse,
    QualityResponse,
)


def _error(code: str, message: str, status: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status)


def _validate_nutrients(payload: FoodWrite) -> dict[str, tuple[Decimal, str, str | None, bool]]:
    values: dict[str, tuple[Decimal, str, str | None, bool]] = {}
    for item in payload.nutrients:
        definition = NUTRIENT_BY_CODE.get(item.nutrient_code)
        if definition is None or not definition.active:
            raise _error("NUTRIENT_NOT_FOUND", "Dieser Nährstoff ist nicht verfügbar.")
        if item.nutrient_code in values:
            raise _error("FOOD_VALIDATION_ERROR", "Ein Nährstoff wurde mehrfach angegeben.")
        if item.unit != definition.canonical_unit:
            raise _error(
                "NUTRIENT_UNIT_MISMATCH",
                "Für "
                f"{definition.display_name_de} ist die Einheit "
                f"{definition.canonical_unit} erforderlich.",
            )
        values[item.nutrient_code] = (item.amount, item.unit, item.source_note, item.is_estimated)
    if "energy_kj" in values:
        raise _error(
            "FOOD_VALIDATION_ERROR", "Bitte gib Energie nur in kcal ein; kJ wird berechnet."
        )
    if "salt" in values and "sodium" in values:
        expected = salt_to_sodium(values["salt"][0])
        if abs(expected - values["sodium"][0]) > Decimal("0.001"):
            raise _error("INCONSISTENT_SALT_SODIUM", "Salz- und Natriumwert passen nicht zusammen.")
    missing = CORE_CODES - values.keys()
    if missing and not payload.confirm_incomplete:
        raise _error(
            "INCOMPLETE_BASIC_NUTRITION",
            "Grundnährwerte fehlen. Bestätige, dass du unvollständig speichern möchtest.",
            409,
        )
    return values


def _validate_measures(payload: FoodWrite) -> None:
    for item in payload.measures:
        if item.equivalent_unit != payload.reference_unit and payload.density_g_per_ml is None:
            raise _error(
                "INVALID_MEASURE_CONVERSION",
                "Die Maßeinheit muss ohne Dichte zur Bezugsbasis passen.",
            )


def _replace_children(
    food: Food, payload: FoodWrite, values: dict[str, tuple[Decimal, str, str | None, bool]]
) -> None:
    food.nutrients.clear()
    for code, (amount, unit, note, estimated) in values.items():
        food.nutrients.append(
            FoodNutrient(
                nutrient_code=code,
                amount=amount,
                unit=unit,
                value_source="user_entered",
                source_note=note,
                is_estimated=estimated,
            )
        )
    food.measures.clear()
    for item in payload.measures:
        food.measures.append(
            FoodMeasure(
                name=item.name.strip(),
                quantity=item.quantity,
                unit_code=item.unit_code,
                equivalent_quantity=item.equivalent_quantity,
                equivalent_unit=item.equivalent_unit,
                is_estimated=item.is_estimated,
                source_type="user_entered",
                note=item.note,
            )
        )


def create_food(session: Session, profile_id: UUID, payload: FoodWrite) -> FoodResponse:
    values = _validate_nutrients(payload)
    _validate_measures(payload)
    if (
        repository.duplicates(session, profile_id, payload.name, payload.brand)
        and not payload.confirm_duplicate
    ):
        raise _error(
            "FOOD_DUPLICATE_WARNING",
            "Ein Lebensmittel mit diesem Namen und dieser Marke ist bereits vorhanden.",
            409,
        )
    food = Food(
        owner_profile_id=profile_id,
        name=payload.name,
        normalized_name=payload.name.casefold(),
        brand=payload.brand,
        normalized_brand=(payload.brand.casefold() if payload.brand else None),
        description=payload.description,
        category_code=payload.category_code,
        food_type="user_created",
        source_type="user_entered",
        reference_quantity=Decimal(100),
        reference_unit=payload.reference_unit,
        density_g_per_ml=payload.density_g_per_ml,
    )
    _replace_children(food, payload, values)
    try:
        session.add(food)
        session.commit()
        session.refresh(food)
        return serialize(food)
    except Exception:
        session.rollback()
        raise


def import_barcode_food(
    session: Session, profile_id: UUID, payload: BarcodeImportRequest
) -> FoodResponse:
    preview = payload.preview
    existing = repository.by_external_id(session, profile_id, "open_food_facts", preview.barcode)
    if existing is not None:
        raise _error(
            "FOOD_DUPLICATE_WARNING",
            "Dieses Barcode-Produkt ist bereits gespeichert.",
            409,
        )
    write = FoodWrite(
        name=preview.name,
        brand=preview.brand,
        reference_unit=preview.reference_unit,
        nutrients=preview.nutrients,
        confirm_incomplete=payload.confirm_incomplete,
        confirm_duplicate=payload.confirm_duplicate,
    )
    values = _validate_nutrients(write)
    if (
        repository.duplicates(session, profile_id, write.name, write.brand)
        and not payload.confirm_duplicate
    ):
        raise _error(
            "FOOD_DUPLICATE_WARNING",
            "Ein Lebensmittel mit diesem Namen und dieser Marke ist bereits vorhanden.",
            409,
        )
    food = Food(
        owner_profile_id=profile_id,
        name=write.name,
        normalized_name=write.name.casefold(),
        brand=write.brand,
        normalized_brand=write.brand.casefold() if write.brand else None,
        food_type="branded",
        source_type="open_food_facts",
        source_name=preview.source_name,
        source_external_id=preview.barcode,
        source_version=preview.source_version,
        reference_quantity=Decimal(100),
        reference_unit=preview.reference_unit,
    )
    _replace_children(food, write, values)
    for nutrient in food.nutrients:
        nutrient.value_source = "open_food_facts"
        nutrient.source_note = "Importiert aus Open Food Facts; vor dem Speichern geprüft."
    try:
        session.add(food)
        session.commit()
        session.refresh(food)
        return serialize(food)
    except Exception:
        session.rollback()
        raise


def require_food(session: Session, profile_id: UUID, food_id: UUID) -> Food:
    food = repository.get_food(session, profile_id, food_id)
    if food is None:
        raise _error("FOOD_NOT_FOUND", "Das Lebensmittel wurde nicht gefunden.", 404)
    return food


def update_food(
    session: Session, profile_id: UUID, food_id: UUID, payload: FoodWrite
) -> FoodResponse:
    food = require_food(session, profile_id, food_id)
    if food.is_archived:
        raise _error("FOOD_ARCHIVED", "Stelle das Lebensmittel vor dem Bearbeiten wieder her.", 409)
    if food.reference_unit != payload.reference_unit and not payload.confirm_reference_change:
        raise _error(
            "INVALID_REFERENCE_BASIS",
            "Bestätige die Änderung der Bezugsbasis; Werte werden nicht umgerechnet.",
            409,
        )
    values = _validate_nutrients(payload)
    _validate_measures(payload)
    if (
        repository.duplicates(session, profile_id, payload.name, payload.brand, food.id)
        and not payload.confirm_duplicate
    ):
        raise _error(
            "FOOD_DUPLICATE_WARNING",
            "Ein Lebensmittel mit diesem Namen und dieser Marke ist bereits vorhanden.",
            409,
        )
    food.name, food.normalized_name = payload.name, payload.name.casefold()
    food.brand, food.normalized_brand = (
        payload.brand,
        payload.brand.casefold() if payload.brand else None,
    )
    food.description, food.category_code = payload.description, payload.category_code
    food.reference_unit, food.density_g_per_ml = payload.reference_unit, payload.density_g_per_ml
    _replace_children(food, payload, values)
    session.commit()
    return serialize(food)


def archive_food(session: Session, profile_id: UUID, food_id: UUID) -> Food:
    food = require_food(session, profile_id, food_id)
    food.is_archived, food.archived_at = True, datetime.now(UTC)
    session.commit()
    return food


def restore_food(session: Session, profile_id: UUID, food_id: UUID) -> FoodResponse:
    food = require_food(session, profile_id, food_id)
    food.is_archived, food.archived_at = False, None
    session.commit()
    return serialize(food)


def permanently_delete_food(session: Session, profile_id: UUID, food_id: UUID) -> UUID:
    """Permanently delete an owned food and its dependent values."""

    food = require_food(session, profile_id, food_id)
    # Import locally to keep Food Core independent at module import time while
    # still giving callers a stable domain conflict instead of a database 500.
    from app.modules.recipes.models import RecipeIngredient

    recipe_reference = session.scalar(
        select(RecipeIngredient.id).where(RecipeIngredient.food_id == food.id).limit(1)
    )
    if recipe_reference is not None:
        raise _error(
            "FOOD_REFERENCED_BY_RECIPE",
            "Dieses Lebensmittel wird noch in einem Rezept verwendet und kann nicht "
            "dauerhaft gelöscht werden.",
            409,
        )
    deleted_id = food.id
    try:
        session.delete(food)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return deleted_id


def _base_quantity(food: Food, quantity: Decimal, unit: str) -> Decimal:
    if unit == food.reference_unit:
        return quantity
    if food.density_g_per_ml is None:
        raise _error(
            "INCOMPATIBLE_UNIT", "Ohne Dichte ist keine Umrechnung zwischen g und ml möglich."
        )
    if unit == "ml" and food.reference_unit == "g":
        return quantity * food.density_g_per_ml
    if unit == "g" and food.reference_unit == "ml":
        return quantity / food.density_g_per_ml
    raise _error("INCOMPATIBLE_UNIT", "Diese Einheit ist nicht kompatibel.")


def normalize_base_quantity(food: Food, quantity: Decimal, unit: str) -> Decimal:
    """Normalize a direct g/ml quantity to the food's reference unit."""

    return _base_quantity(food, quantity, unit)


def scale_nutrients(food: Food, quantity: Decimal, unit: str) -> dict[str, Decimal]:
    base = _base_quantity(food, quantity, unit)
    return {
        item.nutrient_code: item.amount * base / food.reference_quantity for item in food.nutrients
    }


def convert_measure_to_base_quantity(food: Food, unit_code: str, quantity: Decimal) -> Decimal:
    measure = next((item for item in food.measures if item.unit_code == unit_code), None)
    if measure is None:
        raise _error("INVALID_MEASURE_CONVERSION", "Dieses Haushaltsmaß ist nicht vorhanden.", 404)
    converted = measure.equivalent_quantity * quantity / measure.quantity
    return _base_quantity(food, converted, measure.equivalent_unit)


def serialize(food: Food) -> FoodResponse:
    nutrients = [
        NutrientResponse(
            nutrient_code=n.nutrient_code,
            display_name_de=NUTRIENT_BY_CODE[n.nutrient_code].display_name_de,
            amount=n.amount,
            unit=n.unit,
            value_source=n.value_source,
            source_note=n.source_note,
            is_estimated=n.is_estimated,
        )
        for n in food.nutrients
    ]
    known = {item.nutrient_code for item in food.nutrients}
    derived: list[NutrientResponse] = []
    if "energy_kcal" in known:
        value = next(n.amount for n in food.nutrients if n.nutrient_code == "energy_kcal")
        derived.append(
            NutrientResponse(
                nutrient_code="energy_kj",
                display_name_de="Energie",
                amount=kcal_to_kj(value),
                unit="kJ",
                value_source="system_derived",
                source_note="1 kcal = 4,184 kJ",
                is_estimated=False,
                is_derived=True,
            )
        )
    if "salt" in known and "sodium" not in known:
        value = next(n.amount for n in food.nutrients if n.nutrient_code == "salt")
        derived.append(
            NutrientResponse(
                nutrient_code="sodium",
                display_name_de="Natrium",
                amount=salt_to_sodium(value),
                unit="g",
                value_source="system_derived",
                source_note="Salz ÷ 2,5",
                is_estimated=False,
                is_derived=True,
            )
        )
    if "sodium" in known and "salt" not in known:
        value = next(n.amount for n in food.nutrients if n.nutrient_code == "sodium")
        derived.append(
            NutrientResponse(
                nutrient_code="salt",
                display_name_de="Salz",
                amount=sodium_to_salt(value),
                unit="g",
                value_source="system_derived",
                source_note="Natrium mal 2,5",
                is_estimated=False,
                is_derived=True,
            )
        )
    quality = calculate_quality(
        known, {item.nutrient_code for item in derived}, sum(m.is_estimated for m in food.measures)
    )
    return FoodResponse(
        id=food.id,
        name=food.name,
        brand=food.brand,
        description=food.description,
        category_code=food.category_code,
        food_type=food.food_type,
        source_type=food.source_type,
        source_name=food.source_name,
        reference_quantity=food.reference_quantity,
        reference_unit=food.reference_unit,
        density_g_per_ml=food.density_g_per_ml,
        is_archived=food.is_archived,
        archived_at=food.archived_at,
        created_at=food.created_at,
        updated_at=food.updated_at,
        nutrients=nutrients + derived,
        measures=[MeasureResponse.model_validate(m) for m in food.measures],
        quality=QualityResponse.model_validate(quality),
    )
