from decimal import Decimal
from uuid import uuid4

from tests.test_consumption_tracking import _empty_day, _meal
from tests.test_pantry_core import _create_lot, _locations
from tests.test_recipe_core import create_food, recipe_payload


def _food_entry(client, day, meal, food_id, quantity="250"):
    response = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food_id,
            "entered_quantity": quantity,
            "entered_unit_code": "g",
            "client_operation_id": str(uuid4()),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_direct_food_preview_apply_idempotency_and_reversal(client, seeded_database, saved_profile):
    food = create_food(client, name="Abgleich-Reis")
    lot = _create_lot(
        client,
        food["id"],
        _locations(client)[0]["id"],
        quantity="500",
        unit_code="g",
        best_before_date="2026-08-20",
    ).json()
    day = _empty_day(client, "2026-07-30")
    entry = _food_entry(client, day, _meal(client, day), food["id"])
    current = client.get(f"/api/v1/consumption-days/{day['id']}").json()
    request = {
        "expected_day_version": current["version"],
        "entries": [
            {
                "consumption_entry_id": entry["id"],
                "expected_entry_version": entry["version"],
                "source_context": "from_pantry",
                "selected_pantry_quantity": "250",
            }
        ],
    }
    preview = client.post(
        f"/api/v1/consumption-days/{day['id']}/pantry-reconciliation/preview",
        json=request,
    )
    assert preview.status_code == 200, preview.text
    requirement = preview.json()["entries"][0]["requirements"][0]
    assert Decimal(requirement["theoretical_required_quantity"]) == 250
    assert Decimal(requirement["uncovered_quantity"]) == 0
    assert requirement["allocations"][0]["stock_lot_id"] == lot["id"]

    operation = str(uuid4())
    apply_payload = {
        "client_operation_id": operation,
        "preview_token": preview.json()["preview_token"],
        "preview": request,
    }
    applied = client.post(
        f"/api/v1/consumption-days/{day['id']}/pantry-reconciliation/apply",
        json=apply_payload,
    )
    duplicate = client.post(
        f"/api/v1/consumption-days/{day['id']}/pantry-reconciliation/apply",
        json=apply_payload,
    )
    assert applied.status_code == duplicate.status_code == 200, applied.text
    assert applied.json()["id"] == duplicate.json()["id"]
    assert (
        Decimal(client.get(f"/api/v1/pantry/items/{lot['id']}").json()["current_quantity"]) == 250
    )
    allocation = applied.json()["requirements"][0]["allocations"][0]

    reversal_request = {
        "reason": "wrong_quantity",
        "selections": [{"allocation_id": allocation["id"], "quantity": "100"}],
    }
    reversal_preview = client.post(
        f"/api/v1/pantry-consumption-reconciliations/{applied.json()['id']}/reversal-preview",
        json=reversal_request,
    )
    assert reversal_preview.status_code == 200, reversal_preview.text
    reversed_result = client.post(
        f"/api/v1/pantry-consumption-reconciliations/{applied.json()['id']}/reverse",
        json={
            "client_operation_id": str(uuid4()),
            "preview_token": reversal_preview.json()["preview_token"],
            "preview": reversal_request,
        },
    )
    assert reversed_result.status_code == 200, reversed_result.text
    assert reversed_result.json()["status"] == "partially_reversed"
    assert (
        Decimal(client.get(f"/api/v1/pantry/items/{lot['id']}").json()["current_quantity"]) == 350
    )
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200, exported.text
    batches = exported.json()["data"]["pantry_consumption_reconciliation"]["batches"]
    assert batches[0]["requirements"][0]["allocations"][0]["reversal_allocations"]
    deletion_preview = client.get(
        f"/api/v1/consumption-days/{day['id']}/entries/{entry['id']}"
        "/pantry-reconciliation/deletion-preview"
    )
    assert deletion_preview.json()["requires_resolution"] is True
    deleted = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries/{entry['id']}"
        "/pantry-reconciliation/delete-with-resolution",
        json={"policy": "reverse_and_delete", "client_operation_id": str(uuid4())},
    )
    assert deleted.status_code == 200, deleted.text
    assert Decimal(
        client.get(f"/api/v1/pantry/items/{lot['id']}").json()["current_quantity"]
    ) == Decimal("500")


def test_recipe_snapshot_is_historical_and_optional_is_not_suggested(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Historische Zutat")
    recipe = client.post(
        "/api/v1/recipes",
        json=recipe_payload(
            food["id"],
            servings="2",
            ingredients=[
                {
                    "food_id": food["id"],
                    "quantity": "400",
                    "unit_type": "base",
                    "unit_code": "g",
                    "is_optional": True,
                }
            ],
        ),
    ).json()
    _create_lot(client, food["id"], _locations(client)[0]["id"], quantity="500", unit_code="g")
    day = _empty_day(client, "2026-07-29")
    meal = _meal(client, day)
    entry = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "recipe",
            "recipe_id": recipe["id"],
            "recipe_portion_count": "0.5",
            "client_operation_id": str(uuid4()),
        },
    ).json()
    client.patch(
        f"/api/v1/recipes/{recipe['id']}",
        json={**recipe_payload(food["id"], servings="2"), "name": "Geändertes Rezept"},
    )
    current = client.get(f"/api/v1/consumption-days/{day['id']}").json()
    preview = client.post(
        f"/api/v1/consumption-days/{day['id']}/pantry-reconciliation/preview",
        json={
            "expected_day_version": current["version"],
            "entries": [
                {
                    "consumption_entry_id": entry["id"],
                    "expected_entry_version": entry["version"],
                    "source_context": "prepared_from_pantry_for_this_entry",
                }
            ],
        },
    )
    assert preview.status_code == 200, preview.text
    requirement = preview.json()["entries"][0]["requirements"][0]
    assert Decimal(requirement["theoretical_required_quantity"]) == 100
    assert requirement["source_context"] == "not_used"
    assert requirement["allocations"] == []
    assert any(
        item["code"] == "PANTRY_CONSUMPTION_RECIPE_THEORETICAL_QUANTITIES"
        for item in preview.json()["warnings"]
    )
