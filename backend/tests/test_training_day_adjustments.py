from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.core.branding import CONSENT_TEXT_VERSION
from app.modules.training_day_adjustments import engine


def _assessment(client):
    assert (
        client.post(
            "/api/v1/privacy/consents",
            json={
                "purpose_code": "nutrition_assessment_calculation",
                "consent_text_version": CONSENT_TEXT_VERSION,
                "affirmed": True,
                "source": "android_onboarding",
            },
        ).status_code
        == 201
    )
    response = client.post("/api/v1/assessments", json={"client_request_id": str(uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


def _session(client, day="2026-08-03", inclusion="additional_to_baseline"):
    response = client.post(
        "/api/v1/training-sessions",
        json={
            "session_date": day,
            "sport_type": "strength_training",
            "session_type": "strength",
            "planned_duration_minutes": 90,
            "perceived_intensity": "hard",
            "baseline_inclusion": inclusion,
            "title": "Training",
            "note": "privat",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_session_lifecycle_and_unknown_is_default(client, seeded_database, saved_profile):
    created = _session(client, inclusion="unknown")
    assert created["baseline_inclusion"] == "unknown"
    completed = client.post(f"/api/v1/training-sessions/{created['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    cancelled = client.post(f"/api/v1/training-sessions/{created['id']}/cancel")
    assert cancelled.json()["status"] == "cancelled"
    assert client.get("/api/v1/training-sessions").json() == []
    restored = client.post(f"/api/v1/training-sessions/{created['id']}/restore")
    assert restored.json()["status"] == "planned"


def test_engine_weekly_redistribution_is_decimal_balanced():
    start = date(2026, 8, 3)
    days = [(start + timedelta(days=i), "high" if i in {0, 2, 4} else "rest") for i in range(7)]
    result = engine.redistribute(
        days,
        Decimal("2500"),
        Decimal("300"),
        Decimal("250"),
        Decimal("0.15"),
        Decimal("1800"),
        Decimal("0.75"),
    )
    assert sum((item["delta"] for item in result), Decimal(0)).copy_abs() < Decimal("0.01")
    assert len(result) == 7


def test_preview_apply_link_daily_plan_idempotency_and_immutability(
    client, seeded_database, saved_profile
):
    assessment = _assessment(client)
    training = _session(client)
    request = {
        "scope": "single_day",
        "date": "2026-08-03",
        "source_assessment_id": assessment["id"],
        "strategy": "bounded_additive",
    }
    preview = client.post("/api/v1/training-day-adjustments/preview", json=request)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["days"][0]["selected_energy_delta_kcal"] != "0"
    operation = str(uuid4())
    apply = client.post(
        "/api/v1/training-day-adjustments/apply",
        json={
            "preview_token": body["preview_token"],
            "client_operation_id": operation,
            "preview": request,
            "link_to_daily_plan_dates": ["2026-08-03"],
            "create_missing_plan_dates": ["2026-08-03"],
        },
    )
    assert apply.status_code == 200, apply.text
    duplicate = client.post(
        "/api/v1/training-day-adjustments/apply",
        json={
            "preview_token": body["preview_token"],
            "client_operation_id": operation,
            "preview": request,
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == apply.json()["id"]
    plan = client.get("/api/v1/daily-meal-plans/by-date/2026-08-03")
    assert plan.status_code == 200
    assert plan.json()["target_basis"]["training_day_adjustment_id"] is not None
    source_after = client.get(f"/api/v1/assessments/{assessment['id']}")
    assert source_after.json()["summary"] == assessment["summary"]
    changed = dict(training)
    changed.update({"planned_duration_minutes": 120, "expected_version": training["version"]})
    assert (
        client.request(
            "PATCH", f"/api/v1/training-sessions/{training['id']}", json=changed
        ).status_code
        == 200
    )
    plan_after = client.get("/api/v1/daily-meal-plans/by-date/2026-08-03")
    assert plan_after.json()["target_basis"] == plan.json()["target_basis"]


def test_unknown_blocks_additive_and_stale_preview(client, seeded_database, saved_profile):
    assessment = _assessment(client)
    training = _session(client, inclusion="unknown")
    request = {
        "scope": "single_day",
        "date": "2026-08-03",
        "source_assessment_id": assessment["id"],
        "strategy": "bounded_additive",
    }
    preview = client.post("/api/v1/training-day-adjustments/preview", json=request).json()
    assert preview["days"][0]["selected_energy_delta_kcal"] == "0"
    changed = dict(training)
    changed.update({"planned_duration_minutes": 100, "expected_version": training["version"]})
    assert (
        client.request(
            "PATCH", f"/api/v1/training-sessions/{training['id']}", json=changed
        ).status_code
        == 200
    )
    stale = client.post(
        "/api/v1/training-day-adjustments/apply",
        json={
            "preview_token": preview["preview_token"],
            "client_operation_id": str(uuid4()),
            "preview": request,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "TRAINING_ADJUSTMENT_PREVIEW_STALE"
