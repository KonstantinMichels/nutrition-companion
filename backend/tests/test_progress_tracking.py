from datetime import date, time
from decimal import Decimal

from sqlalchemy import func, select

from app.modules.progress_tracking.engine import (
    WeightPoint,
    interval_changes,
    linear_trend,
    representatives,
    rolling,
)
from app.modules.progress_tracking.models import BodyWeightObservation


def test_same_day_latest_time_and_decimal_rolling_average():
    points = representatives(
        [
            WeightPoint("a", date(2026, 7, 1), Decimal("80.0"), time(8), 1),
            WeightPoint("b", date(2026, 7, 1), Decimal("81.0"), time(20), 2),
            WeightPoint("c", date(2026, 7, 4), Decimal("79.0"), None, 3),
        ]
    )
    assert [p.id for p in points] == ["b", "c"]
    assert rolling(points, 7)[-1]["value_kg"] == Decimal("80.0")


def test_linear_trend_and_interval_boundary_tolerance():
    points = [
        WeightPoint("a", date(2026, 7, 1), Decimal("82")),
        WeightPoint("b", date(2026, 7, 8), Decimal("81")),
        WeightPoint("c", date(2026, 7, 15), Decimal("80")),
    ]
    trend = linear_trend(points)
    assert trend["direction"] == "decreasing"
    assert trend["kg_per_week"] == Decimal("-1")
    assert interval_changes(points, date(2026, 7, 15))[1]["change_kg"] == Decimal("-2")


def test_weight_api_conversion_history_overview_edit_and_hard_delete(client, saved_profile):
    first = client.post(
        "/api/v1/progress/weight-observations",
        json={
            "observed_on": "2026-07-01",
            "entered_weight": "220.462262",
            "entered_unit": "lb",
            "measurement_context": "morning",
            "note": "privat",
        },
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert Decimal(body["normalized_weight_kg"]) == Decimal("99.99999992")
    assert Decimal(body["entered_weight"]) == Decimal("220.46226200")
    second = client.post(
        "/api/v1/progress/weight-observations",
        json={
            "observed_on": "2026-07-10",
            "entered_weight": "99",
            "entered_unit": "kg",
        },
    )
    assert second.status_code == 201, second.text
    overview = client.get(
        "/api/v1/progress/overview?date_from=2026-07-01&date_to=2026-07-10&rolling_window_days=7"
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["data_quality"]["representative_day_count"] == 2
    invalid_window = client.get("/api/v1/progress/overview?rolling_window_days=10")
    assert invalid_window.status_code == 422
    assert invalid_window.json()["error"]["code"] == "PROGRESS_INVALID_ROLLING_WINDOW"
    body["entered_weight"] = "219"
    body["expected_version"] = body["version"]
    edited = client.request(
        "PATCH", f"/api/v1/progress/weight-observations/{body['id']}", json=body
    )
    assert edited.status_code == 200, edited.text
    deleted = client.delete(f"/api/v1/progress/weight-observations/{body['id']}?expected_version=2")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/progress/weight-observations/{body['id']}").status_code == 404


def test_measurement_composition_and_goal_lifecycle(client, saved_profile):
    measurement = client.post(
        "/api/v1/progress/body-measurements",
        json={
            "measurement_type": "waist",
            "observed_on": "2026-07-01",
            "entered_value": "40",
            "entered_unit": "in",
        },
    )
    assert measurement.status_code == 201
    assert Decimal(measurement.json()["normalized_value_cm"]) == Decimal("101.6000")
    composition = client.post(
        "/api/v1/progress/body-composition",
        json={
            "observed_on": "2026-07-01",
            "body_fat_percent": "20",
            "measurement_method": "bioelectrical_impedance",
        },
    )
    assert composition.status_code == 201
    goal = client.post(
        "/api/v1/progress/goals",
        json={
            "goal_type": "maintain_weight",
            "start_date": "2026-07-01",
            "target_weight_min_kg": "78",
            "target_weight_max_kg": "82",
        },
    )
    assert goal.status_code == 201, goal.text
    conflict = client.post(
        "/api/v1/progress/goals",
        json={"goal_type": "lose_weight", "start_date": "2026-07-02", "target_weight_kg": "75"},
    )
    assert conflict.status_code == 409
    completed = client.post(
        f"/api/v1/progress/goals/{goal.json()['id']}/complete?expected_version=1"
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_future_and_unusual_weight_require_confirmation(client, saved_profile):
    assert (
        client.post(
            "/api/v1/progress/weight-observations",
            json={"observed_on": "2099-01-01", "entered_weight": "80", "entered_unit": "kg"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/progress/weight-observations",
            json={"observed_on": "2026-07-01", "entered_weight": "80", "entered_unit": "kg"},
        ).status_code
        == 201
    )
    unusual = client.post(
        "/api/v1/progress/weight-observations",
        json={"observed_on": "2026-07-03", "entered_weight": "90", "entered_unit": "kg"},
    )
    assert unusual.status_code == 409
    assert unusual.json()["error"]["code"] == "PROGRESS_PLAUSIBILITY_CONFIRMATION_REQUIRED"


def test_progress_export_and_complete_profile_deletion(client, saved_profile, db_session):
    created = client.post(
        "/api/v1/progress/weight-observations",
        json={
            "observed_on": "2026-07-01",
            "entered_weight": "81.25",
            "entered_unit": "kg",
            "note": "nur im Export",
        },
    )
    assert created.status_code == 201
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200
    progress = exported.json()["data"]["progress_tracking"]
    assert progress["weight_observations"][0]["entered_weight"] == "81.25000000"
    assert progress["weight_observations"][0]["note"] == "nur im Export"
    deleted = client.request("DELETE", "/api/v1/profile", json={"confirm": True})
    assert deleted.status_code == 200
    assert db_session.scalar(select(func.count()).select_from(BodyWeightObservation)) == 0
