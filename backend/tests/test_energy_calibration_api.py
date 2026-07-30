from datetime import date, timedelta
from uuid import uuid4

from app.core.branding import CONSENT_TEXT_VERSION


def test_preview_apply_revision_history_and_stale_token(client, seeded_database, saved_profile):
    consent = client.post(
        "/api/v1/privacy/consents",
        json={
            "purpose_code": "nutrition_assessment_calculation",
            "consent_text_version": CONSENT_TEXT_VERSION,
            "affirmed": True,
            "source": "android_onboarding",
        },
    )
    assert consent.status_code == 201
    source = client.post("/api/v1/assessments", json={"client_request_id": str(uuid4())})
    assert source.status_code == 201, source.text

    start = date(2026, 7, 1)
    for index in range(10):
        response = client.post(
            "/api/v1/progress/weight-observations",
            json={
                "observed_on": (start + timedelta(days=index * 3)).isoformat(),
                "entered_weight": str(82 - index * 0.015),
                "entered_unit": "kg",
                "confirm_unusual_change": True,
            },
        )
        assert response.status_code == 201, response.text

    request = {
        "source_assessment_id": source.json()["id"],
        "window_start": "2026-07-01",
        "window_end": "2026-07-28",
        "adherence": "high",
        "context_stability": "stable",
    }
    preview = client.post("/api/v1/energy-calibration/preview", json=request)
    assert preview.status_code == 200, preview.text
    assert preview.json()["proposal"]["available"] is True
    operation_id = str(uuid4())
    applied = client.post(
        "/api/v1/energy-calibration/apply",
        json={
            "client_operation_id": operation_id,
            "preview_token": preview.json()["preview_token"],
            "preview": request,
        },
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["created_assessment_id"] != source.json()["id"]
    duplicate = client.post(
        "/api/v1/energy-calibration/apply",
        json={
            "client_operation_id": operation_id,
            "preview_token": preview.json()["preview_token"],
            "preview": request,
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == applied.json()["id"]
    history = client.get("/api/v1/energy-calibration/history")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1

    stale = client.post(
        "/api/v1/energy-calibration/apply",
        json={
            "client_operation_id": str(uuid4()),
            "preview_token": preview.json()["preview_token"],
            "preview": request,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "ENERGY_CALIBRATION_PREVIEW_STALE"
