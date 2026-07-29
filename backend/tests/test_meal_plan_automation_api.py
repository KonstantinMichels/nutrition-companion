from uuid import uuid4

from tests.test_recipe_core import create_food, recipe_payload
from tests.test_recipe_target_comparison import _create_assessment


def _preferences(client):
    return client.post(
        "/api/v1/meal-plan-automation/preferences",
        json={"name": "Standard", "is_default": True},
    )


def test_preferences_defaults_archive_restore_and_weight_validation(
    client, seeded_database, saved_profile
):
    created = _preferences(client)
    assert created.status_code == 201, created.text
    body = created.json()
    assert [slot["slot_code"] for slot in body["slots"]] == ["breakfast", "lunch", "dinner"]
    assert body["scoring_weights"]["nutrition_target_fit"] == "2"
    assert (
        client.delete(f"/api/v1/meal-plan-automation/preferences/{body['id']}").status_code == 200
    )
    restored = client.post(f"/api/v1/meal-plan-automation/preferences/{body['id']}/restore")
    assert restored.json()["is_archived"] is False
    invalid = client.post(
        "/api/v1/meal-plan-automation/preferences",
        json={"name": "Ungültig", "scoring_weights": {"meal_slot_fit": "-1"}},
    )
    assert invalid.status_code == 422


def test_preferences_can_be_replaced_and_only_one_is_default(
    client, seeded_database, saved_profile
):
    first = _preferences(client).json()
    second = client.post(
        "/api/v1/meal-plan-automation/preferences",
        json={"name": "Schnell", "is_default": True},
    ).json()
    values = client.get("/api/v1/meal-plan-automation/preferences").json()
    assert [item["id"] for item in values if item["is_default"]] == [second["id"]]
    replacement = {
        key: value for key, value in first.items() if key not in {"id", "updated_at", "is_archived"}
    }
    replacement["name"] = "Werktag"
    replacement["slots"] = [
        {key: value for key, value in slot.items() if key != "id"} for slot in replacement["slots"]
    ]
    updated = client.request(
        "PATCH", f"/api/v1/meal-plan-automation/preferences/{first['id']}", json=replacement
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Werktag"


def test_generate_is_transient_and_apply_is_idempotent(client, seeded_database, saved_profile):
    _create_assessment(client)
    food = create_food(client, name="Hafergericht")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    preferences = _preferences(client).json()
    generation = {
        "preferences_id": preferences["id"],
        "scope": "single_day",
        "plan_date": "2026-08-03",
    }
    draft = client.post("/api/v1/meal-plan-automation/generate", json=generation)
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["engine"] == "optimizer"
    assert body["solver"]["status"] in {"optimal", "feasible"}
    assert body["solver"]["version"] == "9.14.6206"
    assert body["solver"]["num_search_workers"] == 1
    assert body["candidate_summary"]["solver_candidate_count"] > 0
    assert body["days"][0]["proposed_meals"][0]["recipe_id"] == recipe["id"]
    assert client.get("/api/v1/daily-meal-plans/by-date/2026-08-03").status_code == 404
    operation = str(uuid4())
    request = {
        "client_operation_id": operation,
        "preview_token": body["preview_token"],
        "generation": generation,
        "create_missing_plans": True,
    }
    applied = client.post("/api/v1/meal-plan-automation/apply", json=request)
    assert applied.status_code == 200, applied.text
    assert applied.json()["applied_slot_count"] == 2
    replay = client.post("/api/v1/meal-plan-automation/apply", json=request)
    assert replay.json()["idempotent_replay"] is True
    history = client.get("/api/v1/meal-plan-automation/applications").json()
    assert len(history) == 1
    assert history[0]["client_operation_id"] == operation
    assert history[0]["generation_engine"] == "optimizer"
    assert history[0]["solver_status"] == body["solver"]["status"]
    plan = client.get("/api/v1/daily-meal-plans/by-date/2026-08-03").json()
    assert plan["quality"]["meal_count"] == 2
