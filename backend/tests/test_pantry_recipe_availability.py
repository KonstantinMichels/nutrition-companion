from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.pantry_recipe_availability.engine import Lot, Requirement, calculate
from tests.test_pantry_core import _create_lot, _locations
from tests.test_recipe_core import create_food, recipe_payload


def test_engine_calculates_missing_surplus_maximum_and_tied_limits():
    first, second = uuid4(), uuid4()
    requirements = [
        Requirement(first, "Reis", Decimal("100"), "g", False, False, False, ()),
        Requirement(second, "Tofu", Decimal("50"), "g", False, False, False, ()),
    ]
    now = datetime.now(UTC)
    lots = {
        first: [Lot(uuid4(), uuid4(), "Schrank", Decimal("250"), "g", "valid", None, False, now)],
        second: [
            Lot(uuid4(), uuid4(), "Kühlschrank", Decimal("125"), "g", "no_date", None, False, now)
        ],
    }
    result = calculate(requirements, lots, Decimal("3"), "include_all")
    assert result["availability_state"] == "partially_available"
    assert result["maximum_possible_portions"] == Decimal("2.5")
    assert result["maximum_complete_whole_portions"] == 2
    assert len(result["limiting_ingredients"]) == 2
    assert result["ingredients"][0]["missing_quantity"] == Decimal("50")


def test_engine_date_modes_and_allocation_do_not_mutate_input():
    food_id, now = uuid4(), datetime.now(UTC)
    requirement = Requirement(food_id, "Milch", Decimal("100"), "ml", False, False, False, ())
    values = [
        Lot(uuid4(), uuid4(), "Kühl", Decimal("60"), "ml", "past_use_by", None, False, now),
        Lot(uuid4(), uuid4(), "Kühl", Decimal("50"), "ml", "valid", None, False, now),
    ]
    included = calculate([requirement], {food_id: values}, Decimal(1), "include_all")
    excluded = calculate([requirement], {food_id: values}, Decimal(1), "exclude_past_use_by")
    assert included["availability_state"] == "fully_available"
    assert excluded["availability_state"] == "partially_available"
    assert values[0].quantity == Decimal("60")


def test_detail_api_scales_duplicate_food_and_returns_lot_details(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Kartoffeln")
    payload = recipe_payload(food["id"])
    payload["name"] = "Kartoffelgericht"
    payload["servings"] = "2"
    payload["ingredients"] = [
        {"food_id": food["id"], "quantity": "200", "unit_type": "base", "unit_code": "g"},
        {"food_id": food["id"], "quantity": "100", "unit_type": "base", "unit_code": "g"},
    ]
    recipe = client.post("/api/v1/recipes", json=payload).json()
    location = _locations(client)[0]
    lot = _create_lot(client, food["id"], location["id"], quantity="500", unit_code="g")
    assert lot.status_code == 201

    response = client.get(f"/api/v1/recipes/{recipe['id']}/pantry-availability?portion_count=1,5")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["availability_state"] == "fully_available"
    assert Decimal(body["ingredients"][0]["required_quantity"]) == Decimal("225")
    assert Decimal(body["maximum_possible_portions"]) == Decimal("3.333333333333333333333333333")
    assert body["ingredients"][0]["lot_contributions"][0]["stock_lot_id"] == lot.json()["id"]
    assert (
        client.get("/api/v1/pantry/items").json()["items"][0]["current_quantity"]
        == "500.000000000000000"
    )


def test_summary_filter_and_empty_recipe(client, seeded_database, saved_profile):
    food = create_food(client, name="Reis")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    summaries = client.get("/api/v1/recipes/pantry-availability?availability_state=not_available")
    assert summaries.status_code == 200, summaries.text
    assert summaries.json()["items"][0]["recipe_id"] == recipe["id"]
    assert summaries.json()["items"][0]["missing_ingredient_count"] == 1


def test_detail_api_rejects_zero_portions(client, seeded_database, saved_profile):
    food = create_food(client, name="Haferflocken")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()

    response = client.get(f"/api/v1/recipes/{recipe['id']}/pantry-availability?portion_count=0")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PANTRY_AVAILABILITY_INVALID_PORTION_COUNT"
