from datetime import date
from decimal import Decimal

from app.modules.weekly_meal_planning.service import week_bounds
from tests.test_daily_meal_planning import _payload
from tests.test_recipe_core import create_food, recipe_payload
from tests.test_recipe_target_comparison import _create_assessment


def test_iso_week_normalization_and_boundaries():
    assert week_bounds(date(2026, 7, 27)) == (date(2026, 7, 27), date(2026, 8, 2), 31, 2026)
    assert week_bounds(date(2026, 7, 29)) == (date(2026, 7, 27), date(2026, 8, 2), 31, 2026)
    assert week_bounds(date(2026, 8, 2)) == (date(2026, 7, 27), date(2026, 8, 2), 31, 2026)
    assert week_bounds(date(2021, 1, 1)) == (date(2020, 12, 28), date(2021, 1, 3), 53, 2020)
    assert week_bounds(date(2021, 1, 4)) == (date(2021, 1, 4), date(2021, 1, 10), 1, 2021)


def _sources(client):
    food = create_food(client, name="Wochen-Ei")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    return food, recipe


def test_week_states_totals_partial_average_and_archived_day(
    client, seeded_database, saved_profile
):
    empty = client.post(
        "/api/v1/daily-meal-plans",
        json={"plan_date": "2026-07-27", "use_latest_assessment": False, "meals": []},
    )
    assert empty.status_code == 201
    food, recipe = _sources(client)
    payload = _payload(food["id"], recipe["id"])
    payload["use_latest_assessment"] = False
    planned = client.post("/api/v1/daily-meal-plans", json=payload)
    assert planned.status_code == 201, planned.text
    archived_copy = client.post(
        f"/api/v1/daily-meal-plans/{planned.json()['plan']['id']}/duplicate",
        json={"target_date": "2026-08-01", "copy_assessment": False},
    )
    client.delete(f"/api/v1/daily-meal-plans/{archived_copy.json()['plan']['id']}")

    response = client.get("/api/v1/weekly-meal-plans?anchor_date=2026-07-29")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["week_start"] == "2026-07-27"
    assert body["week_end"] == "2026-08-02"
    assert [item["weekday"] for item in body["days"]] == [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    assert body["days"][0]["state"] == "empty_plan"
    assert body["days"][2]["state"] == "planned"
    assert body["days"][5]["state"] == "archived_only"
    assert body["day_counts"]["planned_days"] == 1
    protein = next(item for item in body["weekly_totals"] if item["nutrient_code"] == "protein")
    assert Decimal(protein["amount"]) > 0
    assert protein["average_per_planned_day"] == protein["amount"]
    assert body["quality"]["quality_level"] == "partial_week"


def test_copy_append_and_atomic_move(client, seeded_database, saved_profile):
    food, recipe = _sources(client)
    payload = _payload(food["id"], recipe["id"])
    payload["use_latest_assessment"] = False
    source = client.post("/api/v1/daily-meal-plans", json=payload).json()
    source_plan_id = source["plan"]["id"]
    source_meal_id = source["meals"][0]["id"]

    copied = client.post(
        "/api/v1/weekly-meal-plans/actions/copy-meal",
        json={
            "source_plan_id": source_plan_id,
            "source_meal_id": source_meal_id,
            "target_date": "2026-07-30",
            "copy_mode": "new_meal",
            "assessment_copy_mode": "none",
        },
    )
    assert copied.status_code == 200, copied.text
    target = client.get("/api/v1/daily-meal-plans/by-date/2026-07-30").json()
    assert target["quality"]["entry_count"] == 1
    target_meal_id = target["meals"][0]["id"]

    appended = client.post(
        "/api/v1/weekly-meal-plans/actions/copy-meal",
        json={
            "source_plan_id": source_plan_id,
            "source_meal_id": source_meal_id,
            "target_date": "2026-07-30",
            "copy_mode": "append_to_existing_meal",
            "target_meal_id": target_meal_id,
        },
    )
    assert appended.status_code == 200, appended.text
    assert (
        client.get("/api/v1/daily-meal-plans/by-date/2026-07-30").json()["quality"]["entry_count"]
        == 2
    )

    moved = client.post(
        "/api/v1/weekly-meal-plans/actions/move-meal",
        json={
            "source_plan_id": source_plan_id,
            "source_meal_id": source_meal_id,
            "target_date": "2026-07-31",
            "copy_mode": "new_meal",
        },
    )
    assert moved.status_code == 200, moved.text
    assert (
        client.get(f"/api/v1/daily-meal-plans/{source_plan_id}").json()["quality"]["meal_count"]
        == 1
    )
    assert (
        client.get("/api/v1/daily-meal-plans/by-date/2026-07-31").json()["quality"]["entry_count"]
        == 1
    )


def test_invalid_target_meal_does_not_remove_source(client, seeded_database, saved_profile):
    food, recipe = _sources(client)
    payload = _payload(food["id"], recipe["id"])
    payload["use_latest_assessment"] = False
    source = client.post("/api/v1/daily-meal-plans", json=payload).json()
    response = client.post(
        "/api/v1/weekly-meal-plans/actions/move-meal",
        json={
            "source_plan_id": source["plan"]["id"],
            "source_meal_id": source["meals"][0]["id"],
            "target_date": "2026-07-30",
            "copy_mode": "append_to_existing_meal",
            "target_meal_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 404
    retained = client.get(f"/api/v1/daily-meal-plans/{source['plan']['id']}").json()
    assert retained["quality"]["meal_count"] == 2


def test_weekly_targets_sum_only_comparable_planned_days(client, seeded_database, saved_profile):
    _create_assessment(client)
    food, recipe = _sources(client)
    payload = _payload(food["id"], recipe["id"])
    first = client.post("/api/v1/daily-meal-plans", json=payload).json()
    copied = client.post(
        f"/api/v1/daily-meal-plans/{first['plan']['id']}/duplicate",
        json={"target_date": "2026-07-30", "copy_assessment": True},
    )
    assert copied.status_code == 201
    body = client.get("/api/v1/weekly-meal-plans?anchor_date=2026-07-29").json()
    energy = next(
        item for item in body["weekly_target_comparison"] if item["nutrient_code"] == "energy_kcal"
    )
    assert energy["target_day_count"] == 2
    assert energy["missing_target_day_count"] == 0
    assert energy["target_basis_status"] == "single_assessment"
    assert energy["target_minimum"] is not None
    assert energy["target_maximum"] is not None
