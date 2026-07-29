from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.modules.daily_meal_planning.engine import ComponentValue, EntryInput, MealInput, calculate
from tests.test_recipe_core import create_food, recipe_payload
from tests.test_recipe_target_comparison import _create_assessment


def _payload(food_id: str, recipe_id: str, measure_id: str | None = None) -> dict[str, object]:
    food_entry: dict[str, object] = {
        "entry_type": "food",
        "food_id": food_id,
        "food_quantity": "2" if measure_id else "150",
        "food_unit_code": "piece" if measure_id else "g",
    }
    if measure_id:
        food_entry["food_measure_id"] = measure_id
    return {
        "plan_date": "2026-07-29",
        "name": "Trainingstag",
        "meals": [
            {
                "meal_type": "breakfast",
                "custom_name": "Frühes Frühstück",
                "planned_time": "07:30",
                "entries": [food_entry],
            },
            {
                "meal_type": "dinner",
                "entries": [
                    {
                        "entry_type": "recipe",
                        "recipe_id": recipe_id,
                        "recipe_portion_count": "1.5",
                    }
                ],
            },
        ],
    }


def test_pure_aggregation_preserves_zero_unknown_and_coverage():
    known_zero = ComponentValue("protein", Decimal(0), "g", 1, 1)
    entry = EntryInput(
        None,
        0,
        "food",
        uuid4(),
        "Wasser",
        None,
        False,
        None,
        Decimal(100),
        "ml",
        None,
        Decimal(100),
        "ml",
        False,
        None,
        (known_zero,),
    )
    result = calculate((MealInput(None, 0, "breakfast", "Frühstück", None, None, (entry,)),))
    protein = next(item for item in result["daily_totals"] if item["nutrient_code"] == "protein")
    fiber = next(item for item in result["daily_totals"] if item["nutrient_code"] == "energy_kcal")
    assert protein["amount"] == 0
    assert protein["is_complete"] is True
    assert fiber["amount"] is None
    assert fiber["coverage_ratio"] == 0


def test_create_preview_update_duplicate_archive_restore_and_export(
    client, seeded_database, saved_profile
):
    assessment = _create_assessment(client)
    food = create_food(
        client,
        name="Ei",
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
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    payload = _payload(food["id"], recipe["id"], food["measures"][0]["id"])

    preview = client.post("/api/v1/daily-meal-plans/preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["plan"]["id"] is None
    assert client.get("/api/v1/daily-meal-plans").json()["total"] == 0

    created = client.post("/api/v1/daily-meal-plans", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["assessment"]["id"] == assessment["id"]
    assert body["quality"]["meal_count"] == 2
    assert body["quality"]["entry_count"] == 2
    assert body["quality"]["estimated_conversion_count"] == 1
    protein = next(item for item in body["daily_totals"] if item["nutrient_code"] == "protein")
    assert Decimal(protein["amount"]) > 0
    assert body["target_comparison"]

    assert client.post("/api/v1/daily-meal-plans", json=payload).status_code == 409
    by_date = client.get("/api/v1/daily-meal-plans/by-date/2026-07-29")
    assert by_date.status_code == 200
    plan_id = body["plan"]["id"]

    duplicate = client.post(
        f"/api/v1/daily-meal-plans/{plan_id}/duplicate",
        json={"target_date": "2026-07-30", "copy_assessment": False},
    )
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["assessment"] is None
    assert duplicate.json()["plan"]["id"] != plan_id
    assert duplicate.json()["quality"]["entry_count"] == 2

    archived = client.delete(f"/api/v1/daily-meal-plans/{plan_id}")
    assert archived.status_code == 200
    assert client.get("/api/v1/daily-meal-plans/by-date/2026-07-29").status_code == 404
    assert client.put(f"/api/v1/daily-meal-plans/{plan_id}", json=payload).status_code == 409
    restored = client.post(f"/api/v1/daily-meal-plans/{plan_id}/restore")
    assert restored.status_code == 200

    export = client.get("/api/v1/privacy/export").json()["data"]
    assert any(item["id"] == plan_id for item in export["daily_meal_plans"])
    deleted_assessments = client.delete("/api/v1/assessments", json={"confirm": True})
    assert deleted_assessments.status_code == 200
    retained = client.get(f"/api/v1/daily-meal-plans/{plan_id}")
    assert retained.status_code == 200
    assert retained.json()["assessment"] is None
    assert retained.json()["target_comparison"] == []
    deleted_profile = client.delete("/api/v1/privacy/all-data", json={"confirm": True})
    assert deleted_profile.status_code == 200
    assert client.get("/api/v1/daily-meal-plans").json()["total"] == 0


def test_without_assessment_validation_archived_sources_and_assessment_deletion(
    client, seeded_database, saved_profile
):
    food = create_food(client)
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    payload = _payload(food["id"], recipe["id"])
    payload["use_latest_assessment"] = False
    created = client.post("/api/v1/daily-meal-plans", json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["assessment"] is None
    assert created.json()["target_comparison"] == []

    invalid = {
        **payload,
        "plan_date": "2026-07-31",
        "meals": [
            {
                "meal_type": "lunch",
                "entries": [
                    {"entry_type": "recipe", "recipe_id": recipe["id"], "recipe_portion_count": "0"}
                ],
            }
        ],
    }
    assert client.post("/api/v1/daily-meal-plans", json=invalid).status_code == 422

    client.delete(f"/api/v1/recipes/{recipe['id']}")
    archived_payload = {**payload, "plan_date": "2026-08-01"}
    response = client.post("/api/v1/daily-meal-plans", json=archived_payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ENTRY_SOURCE_ARCHIVED"

    # Local DATE values are returned unchanged and never pass through UTC conversion.
    assert date.fromisoformat(created.json()["plan"]["plan_date"]) == date(2026, 7, 29)
