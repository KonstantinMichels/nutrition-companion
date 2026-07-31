from decimal import Decimal
from uuid import uuid4

from tests.test_assessment_api import _create_assessment, _grant_consent
from tests.test_daily_meal_planning import _payload
from tests.test_recipe_core import create_food, recipe_payload


def _empty_day(client, value: str = "2026-07-30") -> dict:
    response = client.post(
        "/api/v1/consumption-days",
        json={"consumption_date": value, "target_basis_source": "none"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _meal(client, day: dict) -> dict:
    response = client.post(
        f"/api/v1/consumption-days/{day['id']}/meals",
        json={"meal_type": "lunch", "custom_name": "Spontanes Mittagessen"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_empty_day_manual_food_snapshots_finalize_reopen_and_delete(
    client, seeded_database, saved_profile
):
    day = _empty_day(client)
    assert day["summary"]["quality"]["quality_level"] == "empty"
    meal = _meal(client, day)

    manual = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "manual_unresolved",
            "manual_name": "Unbekannter Snack",
            "client_operation_id": str(uuid4()),
        },
    )
    assert manual.status_code == 201, manual.text
    assert manual.json()["nutrient_snapshot_status"] == "unresolved"

    food = create_food(client, name="Haferdrink")
    operation = str(uuid4())
    payload = {
        "meal_id": meal["id"],
        "entry_type": "food",
        "food_id": food["id"],
        "entered_quantity": "0.25",
        "entered_unit_code": "g",
        "client_operation_id": operation,
    }
    created = client.post(f"/api/v1/consumption-days/{day['id']}/entries", json=payload)
    duplicate = client.post(f"/api/v1/consumption-days/{day['id']}/entries", json=payload)
    assert created.status_code == duplicate.status_code == 201
    assert created.json()["id"] == duplicate.json()["id"]
    protein = next(
        item for item in created.json()["nutrient_snapshots"] if item["nutrient_code"] == "protein"
    )
    assert Decimal(protein["amount"]) >= 0

    current = client.get(f"/api/v1/consumption-days/{day['id']}").json()
    finalize = client.post(
        f"/api/v1/consumption-days/{day['id']}/finalize",
        json={
            "completeness_attestation": "partial",
            "confirm_warnings": True,
            "client_operation_id": str(uuid4()),
            "expected_version": current["version"],
        },
    )
    assert finalize.status_code == 200, finalize.text
    assert finalize.json()["status"] == "finalized"
    assert (
        client.post(
            f"/api/v1/consumption-days/{day['id']}/meals", json={"meal_type": "dinner"}
        ).status_code
        == 409
    )
    reopened = client.post(f"/api/v1/consumption-days/{day['id']}/reopen")
    assert reopened.json()["completeness_attestation"] == "not_declared"
    assert client.delete(f"/api/v1/consumption-days/{day['id']}").status_code == 200
    assert (
        client.get("/api/v1/consumption/weekly-summary?week_start=2026-07-27").json()[
            "missing_day_count"
        ]
        == 7
    )
    future = client.post(
        "/api/v1/consumption-days",
        json={"consumption_date": "2099-01-01", "target_basis_source": "none"},
    )
    assert future.status_code == 422
    assert future.json()["error"]["code"] == "CONSUMPTION_DAY_FUTURE_DATE_NOT_ALLOWED"


def test_plan_initialization_is_pending_then_consumed_and_skipped(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Plan-Apfel")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    plan = client.post(
        "/api/v1/daily-meal-plans",
        json={**_payload(food["id"], recipe["id"]), "use_latest_assessment": False},
    ).json()
    response = client.post(
        "/api/v1/consumption-days/from-daily-plan",
        json={"daily_plan_id": plan["plan"]["id"]},
    )
    assert response.status_code == 201, response.text
    day = response.json()
    assert not [entry for meal in day["meals"] for entry in meal["entries"]]
    assert {item["status"] for item in day["planned_entries"]} == {"pending"}

    first, second = day["planned_entries"]
    consumed = client.put(
        f"/api/v1/consumption-days/{day['id']}/planned-entry-outcomes/{first['id']}",
        json={
            "outcome_type": "consumed_as_planned",
            "client_operation_id": str(uuid4()),
            "expected_day_version": day["version"],
        },
    )
    assert consumed.status_code == 200, consumed.text
    assert len(consumed.json()["entries"]) == 1
    current = client.get(f"/api/v1/consumption-days/{day['id']}").json()
    skipped = client.put(
        f"/api/v1/consumption-days/{day['id']}/planned-entry-outcomes/{second['id']}",
        json={
            "outcome_type": "skipped",
            "client_operation_id": str(uuid4()),
            "expected_day_version": current["version"],
        },
    )
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["entries"] == []
    assert client.get(f"/api/v1/daily-meal-plans/{plan['plan']['id']}").status_code == 200


def test_food_units_measure_recipe_snapshot_and_privacy_export(
    client, seeded_database, saved_profile
):
    food = create_food(
        client,
        name="Testmilch",
        unit="ml",
        measures=[
            {
                "name": "Glas",
                "quantity": "1",
                "unit_code": "serving",
                "equivalent_quantity": "250",
                "equivalent_unit": "ml",
                "is_estimated": True,
            }
        ],
    )
    recipe = client.post(
        "/api/v1/recipes",
        json=recipe_payload(
            food["id"],
            name="Milchgericht",
            servings="4",
            ingredients=[
                {
                    "food_id": food["id"],
                    "quantity": "1000",
                    "unit_type": "base",
                    "unit_code": "ml",
                }
            ],
        ),
    ).json()
    day = _empty_day(client, "2026-07-28")
    meal = _meal(client, day)

    liter = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "0.5",
            "entered_unit_code": "l",
            "client_operation_id": str(uuid4()),
        },
    )
    assert liter.status_code == 201, liter.text
    assert Decimal(liter.json()["normalized_quantity"]) == Decimal("500")
    measure = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "2",
            "food_measure_id": food["measures"][0]["id"],
            "client_operation_id": str(uuid4()),
        },
    )
    assert measure.status_code == 201, measure.text
    assert Decimal(measure.json()["normalized_quantity"]) == Decimal("500")
    assert measure.json()["conversion_estimated"] is True
    recipe_entry = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "recipe",
            "recipe_id": recipe["id"],
            "recipe_portion_count": "0.25",
            "client_operation_id": str(uuid4()),
        },
    )
    assert recipe_entry.status_code == 201, recipe_entry.text
    assert Decimal(recipe_entry.json()["recipe_portion_count"]) == Decimal("0.25")

    before = client.get(f"/api/v1/consumption-days/{day['id']}/summary").json()
    client.delete(f"/api/v1/recipes/{recipe['id']}")
    after = client.get(f"/api/v1/consumption-days/{day['id']}/summary").json()
    assert after["actual_totals"] == before["actual_totals"]

    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200, exported.text
    exported_days = exported.json()["data"]["consumption_tracking"]["days"]
    assert any(item["id"] == day["id"] for item in exported_days)
    deleted = client.delete("/api/v1/privacy/consumption-data", json={"confirm": True})
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/api/v1/recipes/{recipe['id']}").status_code == 200


def test_modified_partial_multiple_replacement_and_whole_meal_are_explicit(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Planbrot")
    replacement = create_food(client, name="Ersatzobst")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    plan = client.post(
        "/api/v1/daily-meal-plans",
        json={**_payload(food["id"], recipe["id"]), "use_latest_assessment": False},
    ).json()
    day = client.post(
        "/api/v1/consumption-days/from-daily-plan",
        json={"daily_plan_id": plan["plan"]["id"]},
    ).json()
    first, second = day["planned_entries"]
    first_meal = next(
        meal for meal in day["meals"] if meal["source_plan_meal_id"] == first["meal_id"]
    )
    modified = client.put(
        f"/api/v1/consumption-days/{day['id']}/planned-entry-outcomes/{first['id']}",
        json={
            "outcome_type": "partially_consumed",
            "actual_entries": [
                {
                    "meal_id": first_meal["id"],
                    "entry_type": "food",
                    "food_id": food["id"],
                    "entered_quantity": "0.05",
                    "entered_unit_code": "kg",
                    "client_operation_id": str(uuid4()),
                }
            ],
            "client_operation_id": str(uuid4()),
            "expected_day_version": day["version"],
        },
    )
    assert modified.status_code == 200, modified.text
    assert modified.json()["outcome_type"] == "partially_consumed"
    assert Decimal(modified.json()["entries"][0]["normalized_quantity"]) == Decimal("50")

    current = client.get(f"/api/v1/consumption-days/{day['id']}").json()
    second_meal = next(
        meal for meal in current["meals"] if meal["source_plan_meal_id"] == second["meal_id"]
    )
    replaced = client.put(
        f"/api/v1/consumption-days/{day['id']}/planned-entry-outcomes/{second['id']}",
        json={
            "outcome_type": "replaced",
            "actual_entries": [
                {
                    "meal_id": second_meal["id"],
                    "entry_type": "food",
                    "food_id": replacement["id"],
                    "entered_quantity": "100",
                    "entered_unit_code": "g",
                    "client_operation_id": str(uuid4()),
                },
                {
                    "meal_id": second_meal["id"],
                    "entry_type": "recipe",
                    "recipe_id": recipe["id"],
                    "recipe_portion_count": "0.5",
                    "client_operation_id": str(uuid4()),
                },
            ],
            "client_operation_id": str(uuid4()),
            "expected_day_version": current["version"],
        },
    )
    assert replaced.status_code == 200, replaced.text
    assert len(replaced.json()["entries"]) == 2
    assert (
        client.get(f"/api/v1/daily-meal-plans/{plan['plan']['id']}").json()["quality"][
            "entry_count"
        ]
        == 2
    )


def test_meal_time_reorder_edit_and_confirmed_delete(client, seeded_database, saved_profile):
    day = _empty_day(client, "2026-07-27")
    lunch = client.post(
        f"/api/v1/consumption-days/{day['id']}/meals",
        json={
            "meal_type": "lunch",
            "custom_name": "Spät",
            "consumed_time": "13:15:00",
        },
    ).json()
    dinner = client.post(
        f"/api/v1/consumption-days/{day['id']}/meals",
        json={"meal_type": "dinner", "consumed_time": "19:30:00"},
    ).json()
    current = client.get(f"/api/v1/consumption-days/{day['id']}").json()
    reordered = client.post(
        f"/api/v1/consumption-days/{day['id']}/meals/reorder",
        json={
            "meal_ids": [dinner["id"], lunch["id"]],
            "expected_version": current["version"],
        },
    )
    assert reordered.status_code == 200, reordered.text
    assert reordered.json()["meals"][0]["id"] == dinner["id"]
    edited = client.patch(
        f"/api/v1/consumption-days/{day['id']}/meals/{lunch['id']}",
        json={
            "meal_type": "lunch",
            "custom_name": "Mittag unterwegs",
            "consumed_time": "13:45:00",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["consumed_time"] == "13:45:00"
    food = create_food(client, name="Mahlzeiten-Test")
    entry = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": lunch["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "20",
            "entered_unit_code": "g",
            "client_operation_id": str(uuid4()),
        },
    )
    assert entry.status_code == 201
    assert (
        client.delete(f"/api/v1/consumption-days/{day['id']}/meals/{lunch['id']}").status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/consumption-days/{day['id']}/meals/{lunch['id']}?confirm=true"
        ).status_code
        == 200
    )


def test_entry_edit_keeps_identity_replaces_snapshot_and_rejects_stale_write(
    client, seeded_database, saved_profile
):
    day = _empty_day(client, "2026-07-26")
    meal = _meal(client, day)
    food = create_food(client, name="Editierbar")
    created = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "100",
            "entered_unit_code": "g",
            "client_operation_id": str(uuid4()),
        },
    ).json()
    old_energy = next(
        value["amount"]
        for value in created["nutrient_snapshots"]
        if value["nutrient_code"] == "energy_kcal"
    )
    payload = {
        "meal_id": meal["id"],
        "entry_type": "food",
        "food_id": food["id"],
        "entered_quantity": "200",
        "entered_unit_code": "g",
        "client_operation_id": str(uuid4()),
        "expected_version": created["version"],
    }
    edited = client.patch(
        f"/api/v1/consumption-days/{day['id']}/entries/{created['id']}", json=payload
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["id"] == created["id"]
    assert edited.json()["version"] == created["version"] + 1
    new_energy = next(
        value["amount"]
        for value in edited.json()["nutrient_snapshots"]
        if value["nutrient_code"] == "energy_kcal"
    )
    assert Decimal(new_energy) == Decimal(old_energy) * 2
    assert len(edited.json()["nutrient_snapshots"]) == len(created["nutrient_snapshots"])
    stale = client.patch(
        f"/api/v1/consumption-days/{day['id']}/entries/{created['id']}",
        json={**payload, "client_operation_id": str(uuid4())},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "CONSUMPTION_CONCURRENT_MODIFICATION"


def test_density_validation_archive_preview_history_week_and_all_attestations(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Dichteprodukt", unit="g", density="1.25")
    day = _empty_day(client, "2026-07-25")
    meal = _meal(client, day)
    preview = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries/preview",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "100",
            "entered_unit_code": "ml",
            "client_operation_id": str(uuid4()),
        },
    )
    assert preview.status_code == 200, preview.text
    assert Decimal(preview.json()["normalized_quantity"]) == Decimal("125")
    created = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "100",
            "entered_unit_code": "ml",
            "client_operation_id": str(uuid4()),
        },
    )
    assert created.status_code == 201
    assert client.delete(f"/api/v1/foods/{food['id']}").status_code == 200
    archived = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "1",
            "entered_unit_code": "g",
            "client_operation_id": str(uuid4()),
        },
    )
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "CONSUMPTION_FOOD_ARCHIVED"
    before_delete = client.get(f"/api/v1/consumption-days/{day['id']}/summary").json()
    assert client.delete(f"/api/v1/foods/{food['id']}/permanent").status_code == 200
    after_delete = client.get(f"/api/v1/consumption-days/{day['id']}/summary").json()
    assert after_delete["actual_totals"] == before_delete["actual_totals"]
    current = client.get(f"/api/v1/consumption-days/{day['id']}").json()
    finalized = client.post(
        f"/api/v1/consumption-days/{day['id']}/finalize",
        json={
            "completeness_attestation": "complete_to_best_knowledge",
            "confirm_warnings": True,
            "client_operation_id": str(uuid4()),
            "expected_version": current["version"],
        },
    )
    assert finalized.status_code == 200
    history = client.get(
        "/api/v1/consumption/history?status=finalized&completeness_attestation="
        "complete_to_best_knowledge&has_unresolved_entries=false"
    )
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["actual_energy_kcal"] is not None
    assert "nutrient_snapshots" not in history.json()["items"][0]
    weekly = client.get("/api/v1/consumption/weekly-summary?week_start=2026-07-20")
    assert weekly.status_code == 200
    assert weekly.json()["recorded_day_count"] == 1
    assert weekly.json()["missing_day_count"] == 6
    assert weekly.json()["days"][5]["recorded"] is True


def test_link_existing_day_and_confirm_whole_meal_are_idempotent(
    client, seeded_database, saved_profile
):
    food = create_food(client, name="Link-Produkt")
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    plan = client.post(
        "/api/v1/daily-meal-plans",
        json={**_payload(food["id"], recipe["id"]), "use_latest_assessment": False},
    ).json()
    day = _empty_day(client, plan["plan"]["plan_date"])
    linked = client.post(
        f"/api/v1/consumption-days/{day['id']}/link-daily-plan",
        json={
            "daily_plan_id": plan["plan"]["id"],
            "expected_version": day["version"],
        },
    )
    assert linked.status_code == 200, linked.text
    body = linked.json()
    assert {item["status"] for item in body["planned_entries"]} == {"pending"}
    plan_meal_id = body["planned_entries"][0]["meal_id"]
    operation = str(uuid4())
    first = client.post(
        f"/api/v1/consumption-days/{day['id']}/plan-meals/{plan_meal_id}/confirm",
        json={
            "client_operation_id": operation,
            "expected_day_version": body["version"],
        },
    )
    assert first.status_code == 200, first.text
    count = sum(len(meal["entries"]) for meal in first.json()["day"]["meals"])
    repeated = client.post(
        f"/api/v1/consumption-days/{day['id']}/plan-meals/{plan_meal_id}/confirm",
        json={
            "client_operation_id": operation,
            "expected_day_version": first.json()["day"]["version"],
        },
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["applied_count"] == 0
    assert sum(len(meal["entries"]) for meal in repeated.json()["day"]["meals"]) == count


def test_manual_entry_can_be_resolved_and_complete_profile_deletion_cascades(
    client, seeded_database, saved_profile
):
    day = _empty_day(client, "2026-07-24")
    meal = _meal(client, day)
    manual = client.post(
        f"/api/v1/consumption-days/{day['id']}/entries",
        json={
            "meal_id": meal["id"],
            "entry_type": "manual_unresolved",
            "manual_name": "Snack unterwegs",
            "client_operation_id": str(uuid4()),
        },
    ).json()
    food = create_food(client, name="Geklärter Snack")
    resolved = client.patch(
        f"/api/v1/consumption-days/{day['id']}/entries/{manual['id']}",
        json={
            "meal_id": meal["id"],
            "entry_type": "food",
            "food_id": food["id"],
            "entered_quantity": "35",
            "entered_unit_code": "g",
            "client_operation_id": str(uuid4()),
            "expected_version": manual["version"],
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["id"] == manual["id"]
    assert resolved.json()["nutrient_snapshot_status"] == "complete"
    assert (
        client.get(f"/api/v1/consumption-days/{day['id']}/summary").json()["quality"][
            "unresolved_entry_count"
        ]
        == 0
    )
    deletion = client.request("DELETE", "/api/v1/profile", json={"confirm": True})
    assert deletion.status_code == 200
    assert client.get(f"/api/v1/consumption-days/{day['id']}").status_code == 404


def test_target_basis_snapshot_survives_assessment_deletion(client, seeded_database, saved_profile):
    _grant_consent(client)
    assessment = _create_assessment(client).json()
    day_response = client.post(
        "/api/v1/consumption-days",
        json={
            "consumption_date": "2026-07-23",
            "target_basis_source": "explicit_assessment",
            "assessment_id": assessment["id"],
        },
    )
    assert day_response.status_code == 201, day_response.text
    day = day_response.json()
    assert day["target_basis_snapshot"]["effective_targets"]
    assert day["target_basis_snapshot"]["effective_energy_target_kcal"] is not None
    assert client.delete("/api/v1/assessments", json={"confirm": True}).status_code == 200
    historical = client.get(f"/api/v1/consumption-days/{day['id']}")
    assert historical.status_code == 200, historical.text
    assert historical.json()["assessment_id"] is None
    assert historical.json()["target_basis_snapshot"]["effective_targets"]
