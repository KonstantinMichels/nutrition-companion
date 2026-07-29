from decimal import Decimal
from uuid import uuid4

from app.modules.pantry_aware_shopping.engine import calculate_target
from tests.test_daily_meal_planning import _payload
from tests.test_recipe_core import create_food, recipe_payload


def test_target_formula_separates_target_and_other_commitments():
    result = calculate_target(
        combined_requirement=Decimal("800"),
        pantry_available=Decimal("500"),
        target_commitment=Decimal("100"),
        other_commitment=Decimal("100"),
    )
    assert result["global_additional_need"] == Decimal("100")
    assert result["desired_target_commitment"] == Decimal("200")
    assert result["suggested_target_change"] == Decimal("100")
    assert result["target_change_state"] == "increase"


def _request(recipe_id: str, target_id: str, occurrence: str) -> dict[str, object]:
    return {
        "source_type": "recipe",
        "recipe_id": recipe_id,
        "recipe_portion_count": "1,5",
        "source_occurrence_id": occurrence,
        "target_shopping_list_id": target_id,
        "pantry_date_mode": "include_all",
        "include_other_open_lists": True,
    }


def test_recipe_preview_apply_is_idempotent_and_detects_duplicate_source(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Reis")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    target = client.post("/api/v1/shopping-lists", json={"name": "Wocheneinkauf"}).json()
    occurrence = str(uuid4())
    request = _request(recipe["id"], target["id"], occurrence)

    preview = client.post("/api/v1/pantry-aware-shopping/preview", json=request)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert Decimal(body["items"][0]["new_selected_requirement"]) == Decimal("150")
    assert body["items"][0]["target_change_state"] == "create"
    assert "Der Vorrat wurde nicht reserviert." in body["assumptions"]
    assert client.get(f"/api/v1/shopping-lists/{target['id']}").json()["items"] == []

    operation_id = str(uuid4())
    apply = client.post(
        "/api/v1/pantry-aware-shopping/apply",
        json={
            "client_operation_id": operation_id,
            "preview_token": body["preview_token"],
            "preview": request,
        },
    )
    assert apply.status_code == 200, apply.text
    item = client.get(f"/api/v1/shopping-lists/{target['id']}").json()["items"][0]
    assert Decimal(item["purchase_quantity"]) == Decimal("150")
    assert item["quantity_overridden"] is False

    replay = client.post(
        "/api/v1/pantry-aware-shopping/apply",
        json={
            "client_operation_id": operation_id,
            "preview_token": body["preview_token"],
            "preview": request,
        },
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert len(client.get(f"/api/v1/shopping-lists/{target['id']}").json()["items"]) == 1

    exported = client.get("/api/v1/privacy/export").json()["data"]
    assert len(exported["pantry_aware_shopping_operations"]) == 1
    source = exported["shopping_lists"][0]["items"][0]["sources"][0]
    assert source["source_identity"].startswith(f"recipe:{recipe['id']}:request:{occurrence}")

    duplicate = client.post("/api/v1/pantry-aware-shopping/preview", json=request)
    assert duplicate.status_code == 200
    assert duplicate.json()["items"] == []
    assert duplicate.json()["summary"]["duplicate_source_count"] == 1


def test_completed_target_is_rejected(client, seeded_database, saved_profile):
    food = create_food(client, name="Nudeln")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    target = client.post("/api/v1/shopping-lists", json={"name": "Alt"}).json()
    client.post(f"/api/v1/shopping-lists/{target['id']}/complete")

    response = client.post(
        "/api/v1/pantry-aware-shopping/preview",
        json=_request(recipe["id"], target["id"], str(uuid4())),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PANTRY_AWARE_TARGET_LIST_COMPLETED"


def test_daily_and_weekly_sources_keep_underlying_entry_identity(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Linsen")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    plan_payload = _payload(food["id"], recipe["id"])
    plan_payload["use_latest_assessment"] = False
    plan = client.post("/api/v1/daily-meal-plans", json=plan_payload).json()
    target = client.post("/api/v1/shopping-lists", json={"name": "Planbedarf"}).json()
    base = {
        "target_shopping_list_id": target["id"],
        "include_other_open_lists": True,
    }

    daily = client.post(
        "/api/v1/pantry-aware-shopping/preview",
        json={
            **base,
            "source_type": "daily_plan",
            "daily_plan_id": plan["plan"]["id"],
        },
    )
    assert daily.status_code == 200, daily.text
    daily_identities = {
        source["source_identity"]
        for item in daily.json()["items"]
        for source in item["source_contributions"]
    }
    assert all(
        identity.startswith(f"daily_plan:{plan['plan']['id']}:meal_entry:")
        for identity in daily_identities
    )

    weekly = client.post(
        "/api/v1/pantry-aware-shopping/preview",
        json={
            **base,
            "source_type": "weekly_plan",
            "week_anchor_date": "2026-07-29",
        },
    )
    assert weekly.status_code == 200, weekly.text
    weekly_identities = {
        source["source_identity"]
        for item in weekly.json()["items"]
        for source in item["source_contributions"]
    }
    assert weekly_identities == daily_identities
