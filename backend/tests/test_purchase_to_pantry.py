from decimal import Decimal
from uuid import uuid4

from tests.test_recipe_core import create_food


def _setup(client):
    food = create_food(client, name="Milch", unit="ml")
    shopping = client.post("/api/v1/shopping-lists", json={"name": "Einkauf"}).json()
    item = client.post(
        f"/api/v1/shopping-lists/{shopping['id']}/items",
        json={"food_id": food["id"], "quantity": "2", "unit_code": "l"},
    ).json()
    location = client.get("/api/v1/pantry/locations").json()[1]
    return food, shopping, item, location


def _request(item, location):
    return {
        "items": [
            {
                "shopping_list_item_id": item["id"],
                "actual_quantity": "2",
                "unit_code": "l",
                "mark_item_handoff_completed": True,
                "destinations": [
                    {
                        "destination_type": "new_stock_lot",
                        "pantry_location_id": location["id"],
                        "quantity": "1",
                        "unit_code": "l",
                        "purchase_date": "2026-07-29",
                    },
                    {
                        "destination_type": "new_stock_lot",
                        "pantry_location_id": location["id"],
                        "quantity": "1000",
                        "unit_code": "ml",
                        "use_by_date": "2026-08-05",
                    },
                ],
            }
        ]
    }


def test_preview_is_non_persisting_and_apply_is_atomic_and_idempotent(
    client, seeded_database, saved_profile
):
    _, shopping, item, location = _setup(client)
    payload = _request(item, location)
    preview = client.post(
        f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoff-preview", json=payload
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["summary"]["new_stock_lot_count"] == 2
    assert client.get("/api/v1/pantry/items").json()["total"] == 0
    assert client.get(f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoffs").json() == []

    operation_id = str(uuid4())
    apply_payload = {
        **payload,
        "client_operation_id": operation_id,
        "preview_token": preview.json()["preview_token"],
    }
    applied = client.post(
        f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoff", json=apply_payload
    )
    assert applied.status_code == 201, applied.text
    assert client.get("/api/v1/pantry/items").json()["total"] == 2
    exported = client.get("/api/v1/privacy/export").json()["data"]
    assert len(exported["purchase_to_pantry_handoffs"]) == 1
    assert exported["purchase_to_pantry_handoffs"][0]["items"][0]["shopping_item_name"] == "Milch"
    assert len(client.get(f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoffs").json()) == 1
    detail = client.get(f"/api/v1/shopping-lists/{shopping['id']}").json()
    assert detail["items"][0]["pantry_handoff_state"] == "completed"
    assert Decimal(detail["items"][0]["pantry_transferred_quantity"]) == Decimal("2000")
    assert detail["items"][0]["is_checked"] is False

    duplicate = client.post(
        f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoff", json=apply_payload
    )
    assert duplicate.status_code == 201
    assert client.get("/api/v1/pantry/items").json()["total"] == 2


def test_destination_sum_and_archived_list_are_rejected(client, seeded_database, saved_profile):
    _, shopping, item, location = _setup(client)
    payload = _request(item, location)
    payload["items"][0]["destinations"].pop()
    mismatch = client.post(
        f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoff-preview", json=payload
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "PURCHASE_HANDOFF_DESTINATION_SUM_MISMATCH"
    assert client.get("/api/v1/pantry/items").json()["total"] == 0

    client.delete(f"/api/v1/shopping-lists/{shopping['id']}")
    archived = client.get(f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoff-eligibility")
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "PURCHASE_HANDOFF_LIST_ARCHIVED"


def test_complete_profile_deletion_removes_handoff_links(client, seeded_database, saved_profile):
    _, shopping, item, location = _setup(client)
    payload = _request(item, location)
    preview = client.post(
        f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoff-preview", json=payload
    ).json()
    applied = client.post(
        f"/api/v1/shopping-lists/{shopping['id']}/pantry-handoff",
        json={
            **payload,
            "client_operation_id": str(uuid4()),
            "preview_token": preview["preview_token"],
        },
    )
    assert applied.status_code == 201
    deleted = client.request("DELETE", "/api/v1/profile", json={"confirm": True})
    assert deleted.status_code == 200, deleted.text
