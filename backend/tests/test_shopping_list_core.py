def test_manual_shopping_list_item_lifecycle(client, seeded_database, saved_profile):
    created = client.post("/api/v1/shopping-lists", json={"name": "Wochenende"})
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]

    added = client.post(
        f"/api/v1/shopping-lists/{list_id}/items",
        json={"name": "Spülmittel", "quantity": "2,5", "unit_code": "Flaschen"},
    )
    assert added.status_code == 201, added.text
    item_id = added.json()["id"]
    assert added.json()["manual_quantity"] == "2.5"

    checked = client.post(f"/api/v1/shopping-lists/{list_id}/items/{item_id}/check")
    assert checked.status_code == 200
    assert checked.json()["is_checked"] is True
    assert client.get("/api/v1/shopping-lists").json()["items"][0]["checked_item_count"] == 1

    unchecked = client.request(
        "PATCH",
        f"/api/v1/shopping-lists/{list_id}/items/{item_id}",
        json={"is_checked": False},
    )
    assert unchecked.status_code == 200
    assert unchecked.json()["is_checked"] is False

    completed = client.post(f"/api/v1/shopping-lists/{list_id}/complete")
    assert completed.json()["status"] == "completed"
    assert client.delete(f"/api/v1/shopping-lists/{list_id}").json()["is_archived"] is True
    assert client.post(f"/api/v1/shopping-lists/{list_id}/restore").json()["is_archived"] is False


def test_generation_requires_exactly_one_source(client, seeded_database, saved_profile):
    response = client.post(
        "/api/v1/shopping-lists/generation-preview",
        json={"pantry_considered": True},
    )
    assert response.status_code == 422


def test_shopping_lists_are_in_privacy_export(client, seeded_database, saved_profile):
    assert client.post("/api/v1/shopping-lists", json={"name": "Privat"}).status_code == 201
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200, exported.text
    assert exported.json()["data"]["shopping_lists"][0]["name"] == "Privat"
