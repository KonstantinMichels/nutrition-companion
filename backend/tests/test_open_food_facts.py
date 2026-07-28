from decimal import Decimal

import pytest

from app.core.errors import ApiError
from app.modules.foods import open_food_facts


def off_response() -> dict[str, object]:
    return {
        "product": {
            "code": "12345678",
            "product_name_de": "Test Haferdrink",
            "brands": "Testmarke",
            "quantity": "1 l",
            "product_quantity_unit": "ml",
            "last_modified_t": 1234,
            "nutriments": {
                "energy-kcal_100g": 42,
                "fat_100g": 1.5,
                "carbohydrates_100g": 6.8,
                "proteins_100g": 1.0,
                "salt_100g": 0.1,
                "calcium_100g": 0.12,
            },
        }
    }


def test_maps_off_product_and_converts_milligrams() -> None:
    product = open_food_facts.map_product("12345678", off_response())
    assert product["reference_unit"] == "ml"
    nutrients = {item["nutrient_code"]: item for item in product["nutrients"]}
    assert nutrients["energy_kcal"]["amount"] == "42"
    assert nutrients["calcium"] == {
        "nutrient_code": "calcium",
        "amount": "120.00",
        "unit": "mg",
    }


def test_unknown_off_values_are_not_zero() -> None:
    product = open_food_facts.map_product("12345678", off_response())
    codes = {item["nutrient_code"] for item in product["nutrients"]}
    assert "fiber" not in codes


def test_barcode_validation() -> None:
    assert open_food_facts.normalize_barcode(" 12345678 ") == "12345678"
    with pytest.raises(ApiError) as error:
        open_food_facts.normalize_barcode("ABC")
    assert error.value.code == "INVALID_BARCODE"


def test_barcode_preview_and_import(client, saved_profile, monkeypatch) -> None:
    monkeypatch.setattr(open_food_facts, "fetch_product", lambda _code: off_response())
    preview_response = client.get("/api/v1/foods/barcode/12345678")
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["name"] == "Test Haferdrink"
    imported = client.post(
        "/api/v1/foods/barcode/12345678/import",
        json={"preview": preview},
    )
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert body["source_type"] == "open_food_facts"
    assert body["source_name"] == "Open Food Facts"
    assert Decimal(
        next(n for n in body["nutrients"] if n["nutrient_code"] == "fat")["amount"]
    ) == Decimal("1.5")
