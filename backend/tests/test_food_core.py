from decimal import Decimal

from app.modules.foods.conversions import kcal_to_kj, salt_to_sodium, sodium_to_salt
from app.modules.foods.models import Food, FoodNutrient
from app.modules.foods.service import scale_nutrients


def payload(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "name": "Test Joghurt",
        "brand": "Marke",
        "reference_unit": "g",
        "nutrients": [
            {"nutrient_code": "energy_kcal", "amount": "60.125", "unit": "kcal"},
            {"nutrient_code": "fat", "amount": "0", "unit": "g"},
            {"nutrient_code": "carbohydrate", "amount": "5.2", "unit": "g"},
            {"nutrient_code": "protein", "amount": "10", "unit": "g"},
            {"nutrient_code": "salt", "amount": "0.25", "unit": "g"},
        ],
    }
    result.update(overrides)
    return result


def test_conversions_are_decimal_safe() -> None:
    assert kcal_to_kj(Decimal("1")) == Decimal("4.184")
    assert salt_to_sodium(Decimal("2.5")) == Decimal("1")
    assert sodium_to_salt(Decimal("1")) == Decimal("2.5")


def test_catalog_and_food_lifecycle(client, saved_profile) -> None:
    catalog = client.get("/api/v1/nutrients?basic_only=true")
    assert catalog.status_code == 200
    assert any(
        item["code"] == "protein" and item["display_name_de"] == "Eiweiß" for item in catalog.json()
    )
    created = client.post("/api/v1/foods", json=payload())
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["quality"]["basic_nutrition_complete"] is True
    assert next(n for n in body["nutrients"] if n["nutrient_code"] == "fat")["amount"] == "0E-15"
    assert (
        next(n for n in body["nutrients"] if n["nutrient_code"] == "energy_kj")["is_derived"]
        is True
    )
    assert client.get("/api/v1/foods?query=MARKE").json()["total"] == 1
    food_id = body["id"]
    assert client.delete(f"/api/v1/foods/{food_id}").status_code == 200
    assert client.get("/api/v1/foods").json()["total"] == 0
    assert client.get("/api/v1/foods?include_archived=true").json()["total"] == 1
    assert client.post(f"/api/v1/foods/{food_id}/restore").status_code == 200


def test_unknown_duplicate_and_validation(client, saved_profile) -> None:
    incomplete = payload(
        nutrients=[{"nutrient_code": "energy_kcal", "amount": "1", "unit": "kcal"}]
    )
    assert client.post("/api/v1/foods", json=incomplete).status_code == 409
    incomplete["confirm_incomplete"] = True
    response = client.post("/api/v1/foods", json=incomplete)
    assert response.status_code == 201
    assert {n["nutrient_code"] for n in response.json()["nutrients"]} == {
        "energy_kcal",
        "energy_kj",
    }
    assert (
        client.post("/api/v1/foods", json=incomplete).json()["error"]["code"]
        == "FOOD_DUPLICATE_WARNING"
    )
    bad = payload(
        name="Bad",
        nutrients=[{"nutrient_code": "protein", "amount": "-1", "unit": "g"}],
        confirm_incomplete=True,
    )
    assert client.post("/api/v1/foods", json=bad).status_code == 422


def test_scaling_has_no_premature_rounding() -> None:
    food = Food(name="x", normalized_name="x", reference_quantity=Decimal(100), reference_unit="g")
    food.nutrients = [
        FoodNutrient(
            nutrient_code="protein",
            amount=Decimal("12.3456789"),
            unit="g",
            value_source="user_entered",
        )
    ]
    assert scale_nutrients(food, Decimal("250"), "g")["protein"] == Decimal("30.86419725")


def test_food_is_exported(client, saved_profile) -> None:
    created = client.post("/api/v1/foods", json=payload()).json()
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200
    foods = exported.json()["data"]["user_created_foods"]
    assert foods[0]["id"] == created["id"]
    assert foods[0]["nutrients"][0]["value_source"] == "user_entered"


def test_permanent_delete_removes_food_and_children(client, saved_profile) -> None:
    created = client.post("/api/v1/foods", json=payload()).json()
    response = client.delete(f"/api/v1/foods/{created['id']}/permanent")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert client.get(f"/api/v1/foods/{created['id']}").status_code == 404
    assert client.get("/api/v1/foods?include_archived=true").json()["total"] == 0
