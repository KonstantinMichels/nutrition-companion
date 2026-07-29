from decimal import Decimal
from uuid import uuid4

from tests.test_recipe_core import create_food


def _locations(client):
    response = client.get("/api/v1/pantry/locations")
    assert response.status_code == 200, response.text
    return response.json()


def _create_lot(client, food_id, location_id, **overrides):
    payload = {
        "client_operation_id": str(uuid4()),
        "food_id": food_id,
        "location_id": location_id,
        "quantity": "1.5",
        "unit_code": "kg",
        "best_before_date": "2026-08-01",
    }
    payload.update(overrides)
    return client.post("/api/v1/pantry/items", json=payload)


def test_default_locations_once_and_location_lifecycle(client, seeded_database, saved_profile):
    first = _locations(client)
    second = _locations(client)
    assert [item["name"] for item in first] == [
        "Vorratsschrank",
        "Kühlschrank",
        "Gefrierschrank",
    ]
    assert len(second) == 3
    custom = client.post(
        "/api/v1/pantry/locations",
        json={"name": "Küchenschrank links", "location_type": "kitchen"},
    )
    assert custom.status_code == 201
    location_id = custom.json()["id"]
    renamed = client.request(
        "PATCH",
        f"/api/v1/pantry/locations/{location_id}",
        json={"name": "Küchenschrank rechts", "position": 1},
    )
    assert renamed.json()["name"] == "Küchenschrank rechts"
    assert client.delete(f"/api/v1/pantry/locations/{location_id}").status_code == 200
    restored = client.post(f"/api/v1/pantry/locations/{location_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["is_archived"] is False


def test_stock_normalization_initial_movement_dates_and_idempotency(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Kartoffeln")
    location = _locations(client)[0]
    operation = str(uuid4())
    created = _create_lot(
        client,
        food["id"],
        location["id"],
        client_operation_id=operation,
        purchase_date="2026-07-28",
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert Decimal(body["current_quantity"]) == Decimal("1500")
    assert body["normalized_unit"] == "g"
    assert body["date_status"] in {"expiring_soon", "past_best_before", "valid"}
    assert body["movements"][0]["movement_type"] == "initial_stock"
    duplicate = _create_lot(
        client,
        food["id"],
        location["id"],
        client_operation_id=operation,
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == body["id"]
    assert client.get("/api/v1/pantry/items").json()["total"] == 1


def test_measure_add_consume_discard_correction_and_no_negative_stock(
    client, seeded_database, saved_profile
):
    food = create_food(
        client,
        name="Eier",
        measures=[
            {
                "name": "Stück",
                "quantity": "1",
                "unit_code": "piece",
                "equivalent_quantity": "58",
                "equivalent_unit": "g",
                "is_estimated": True,
            }
        ],
    )
    location = _locations(client)[1]
    measure_id = food["measures"][0]["id"]
    created = _create_lot(
        client,
        food["id"],
        location["id"],
        quantity="6",
        unit_code="piece",
        food_measure_id=measure_id,
    )
    assert created.status_code == 201, created.text
    lot = created.json()
    assert Decimal(lot["current_quantity"]) == Decimal("348")
    assert lot["initial_conversion_estimated"] is True
    lot_id = lot["id"]

    add_id = str(uuid4())
    add_payload = {
        "client_operation_id": add_id,
        "quantity": "2",
        "unit_code": "piece",
        "food_measure_id": measure_id,
    }
    added = client.post(f"/api/v1/pantry/items/{lot_id}/add", json=add_payload)
    assert Decimal(added.json()["current_quantity"]) == Decimal("464")
    duplicate = client.post(f"/api/v1/pantry/items/{lot_id}/add", json=add_payload)
    assert Decimal(duplicate.json()["current_quantity"]) == Decimal("464")

    consumed = client.post(
        f"/api/v1/pantry/items/{lot_id}/consume",
        json={
            "client_operation_id": str(uuid4()),
            "quantity": "1",
            "unit_code": "piece",
            "food_measure_id": measure_id,
        },
    )
    assert Decimal(consumed.json()["current_quantity"]) == Decimal("406")
    insufficient = client.post(
        f"/api/v1/pantry/items/{lot_id}/discard",
        json={
            "client_operation_id": str(uuid4()),
            "quantity": "100",
            "unit_code": "piece",
            "food_measure_id": measure_id,
        },
    )
    assert insufficient.status_code == 409
    corrected = client.post(
        f"/api/v1/pantry/items/{lot_id}/correct",
        json={"client_operation_id": str(uuid4()), "new_total_quantity": "0", "unit_code": "g"},
    )
    assert corrected.json()["is_depleted"] is True
    assert Decimal(corrected.json()["current_quantity"]) == 0


def test_partial_and_full_transfer_availability_and_archive_conflicts(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Reis")
    locations = _locations(client)
    source = _create_lot(client, food["id"], locations[0]["id"], quantity="1000", unit_code="g")
    lot_id = source.json()["id"]
    partial = client.post(
        f"/api/v1/pantry/items/{lot_id}/transfer",
        json={
            "client_operation_id": str(uuid4()),
            "quantity": "250",
            "unit_code": "g",
            "target_location_id": locations[1]["id"],
        },
    )
    assert partial.status_code == 200, partial.text
    target_id = partial.json()["id"]
    assert target_id != lot_id
    assert Decimal(client.get(f"/api/v1/pantry/items/{lot_id}").json()["current_quantity"]) == 750
    availability = client.get(f"/api/v1/pantry/availability?food_id={food['id']}").json()[0]
    assert Decimal(availability["available_quantity"]) == 1000
    assert availability["active_lot_count"] == 2
    assert client.delete(f"/api/v1/pantry/locations/{locations[0]['id']}").status_code == 409

    full = client.post(
        f"/api/v1/pantry/items/{target_id}/transfer",
        json={
            "client_operation_id": str(uuid4()),
            "quantity": "250",
            "unit_code": "g",
            "target_location_id": locations[2]["id"],
        },
    )
    assert full.status_code == 200
    assert full.json()["location"]["id"] == locations[2]["id"]
    archive = client.request(
        "DELETE", f"/api/v1/pantry/items/{lot_id}", json={"confirm_non_depleted": True}
    )
    assert archive.status_code == 200
    available_after = client.get(f"/api/v1/pantry/availability?food_id={food['id']}").json()[0]
    assert Decimal(available_after["available_quantity"]) == 250
    assert client.post(f"/api/v1/pantry/items/{lot_id}/restore").status_code == 200


def test_pantry_privacy_export_and_complete_deletion(client, seeded_database, saved_profile):
    food = create_food(client, name="Haferflocken")
    location = _locations(client)[0]
    lot = _create_lot(client, food["id"], location["id"], quantity="500", unit_code="g")
    assert lot.status_code == 201
    export = client.get("/api/v1/privacy/export").json()["data"]
    assert export["pantry_locations"]
    assert export["pantry_stock_lots"][0]["food_id"] == food["id"]
    assert export["pantry_movements"][0]["movement_type"] == "initial_stock"
    deleted = client.request("DELETE", "/api/v1/privacy/all-data", json={"confirm": True})
    assert deleted.status_code == 200, deleted.text
    assert client.get("/api/v1/pantry/items").json()["total"] == 0
