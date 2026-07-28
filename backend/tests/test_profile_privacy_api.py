from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import NoReturn
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.branding import CONSENT_TEXT_VERSION
from app.core.config import Settings
from app.modules.privacy.models import PrivacyAction
from app.modules.profiles import service as profile_service
from tests.conftest import ApiClient


def test_health_endpoint(client: ApiClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "nutrition-companion-api",
        "environment": "test",
    }
    assert len(response.headers["x-request-id"]) == 16


def test_profile_sections_round_trip(
    client: ApiClient, complete_profile_payload: dict[str, object], saved_profile: None
) -> None:
    profile = client.get("/api/v1/profile")
    assert profile.status_code == 200
    data = profile.json()
    assert Decimal(data["height_cm"]) == Decimal("180.0")
    assert Decimal(data["current_weight_kg"]) == Decimal("82.5")
    assert {item["measurement_type"] for item in data["measurements"]} == {
        "body_fat_percentage",
        "waist_circumference",
        "hip_circumference",
    }
    assert client.get("/api/v1/profile/activity").json()["sports"][0]["sport_type"] == (
        "strength_training"
    )
    assert client.get("/api/v1/profile/goal").json()["goal_type"] == "lose_weight"
    assert (
        client.get("/api/v1/profile/restrictions").json()["restrictions"][0]["value"] == "Erdnuss"
    )
    assert client.get("/api/v1/profile/health-screening").status_code == 200


def test_health_screening_update_refreshes_provenance_timestamp(
    client: ApiClient, saved_profile: None
) -> None:
    first = client.get("/api/v1/profile/health-screening").json()
    updated = client.put(
        "/api/v1/profile/health-screening",
        json={
            "pregnant": False,
            "breastfeeding": False,
            "diagnosed_eating_disorder": False,
            "diabetes": False,
            "kidney_disease": False,
            "liver_disease": False,
            "medically_prescribed_diet": False,
            "serious_metabolic_condition": False,
            "other_professional_nutrition_condition": False,
            "user_note": "Erneut geprüft",
        },
    )
    assert updated.status_code == 200
    previous_time = datetime.fromisoformat(first["screened_at"])
    if previous_time.tzinfo is None:  # SQLite test dialect drops timezone metadata.
        previous_time = previous_time.replace(tzinfo=UTC)
    assert datetime.fromisoformat(updated.json()["screened_at"]) > previous_time


def test_validation_error_is_machine_readable_and_sanitized(client: ApiClient) -> None:
    secret_value = "99999.12345"
    response = client.put(
        "/api/v1/profile",
        json={
            "birth_date": "1990-01-01",
            "physiological_category": "reference_category_a",
            "height_cm": secret_value,
            "current_weight_kg": 80,
            "dietary_preference": "mixed",
        },
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["field_errors"][0]["field"] == "height_cm"
    assert secret_value not in response.text
    assert "input" not in response.text


def test_consent_is_explicit_versioned_and_withdrawable(
    client: ApiClient, seeded_purposes: None, saved_profile: None
) -> None:
    refused = client.post(
        "/api/v1/privacy/consents",
        json={
            "purpose_code": "nutrition_assessment_calculation",
            "consent_text_version": CONSENT_TEXT_VERSION,
            "affirmed": False,
            "source": "android_onboarding",
        },
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "CONSENT_NOT_GRANTED"

    granted = client.post(
        "/api/v1/privacy/consents",
        json={
            "purpose_code": "nutrition_assessment_calculation",
            "consent_text_version": CONSENT_TEXT_VERSION,
            "affirmed": True,
            "source": "android_onboarding",
        },
    )
    assert granted.status_code == 201
    consent_id = UUID(granted.json()["id"])
    assert granted.json()["status"] == "granted"
    assert granted.json()["consent_text_version"] == CONSENT_TEXT_VERSION

    repeated = client.post(
        "/api/v1/privacy/consents",
        json={
            "purpose_code": "nutrition_assessment_calculation",
            "consent_text_version": CONSENT_TEXT_VERSION,
            "affirmed": True,
            "source": "android_onboarding",
        },
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == str(consent_id)
    assert len(client.get("/api/v1/privacy/consents").json()) == 1

    withdrawn = client.post(f"/api/v1/privacy/consents/{consent_id}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert withdrawn.json()["withdrawn_at"] is not None

    granted_again = client.post(
        "/api/v1/privacy/consents",
        json={
            "purpose_code": "nutrition_assessment_calculation",
            "consent_text_version": CONSENT_TEXT_VERSION,
            "affirmed": True,
            "source": "android_onboarding",
        },
    )
    assert granted_again.status_code == 201
    assert granted_again.json()["status"] == "granted"
    assert granted_again.json()["id"] != str(consent_id)
    assert len(client.get("/api/v1/privacy/consents").json()) == 2


def test_export_is_explicit_and_excludes_privacy_action_metadata(
    client: ApiClient, seeded_purposes: None, saved_profile: None, db_session: Session
) -> None:
    response = client.get("/api/v1/privacy/export")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["profile"]["birth_date"] == "1990-06-15"
    assert data["dietary_restrictions"][0]["value"] == "Erdnuss"
    assert [item["action_type"] for item in data["privacy_actions"]] == ["export_requested"]
    assert data["profile"]["current_weight_kg"] == "82.500"
    actions = list(db_session.scalars(select(PrivacyAction)))
    assert actions[-1].action_type == "export_requested"
    assert not hasattr(actions[-1], "details")


def test_complete_deletion_is_hard_and_leaves_no_profile_identifier(
    client: ApiClient, saved_profile: None, db_session: Session
) -> None:
    response = client.request("DELETE", "/api/v1/profile", json={"confirm": True})
    assert response.status_code == 200
    assert response.json()["scope"] == "complete_profile"
    assert client.get("/api/v1/profile").status_code == 404

    action = db_session.scalar(
        select(PrivacyAction).where(PrivacyAction.action_type == "profile_deleted")
    )
    assert action is not None
    assert action.profile_id is None


def test_unmatched_path_is_sanitized_in_error_and_log(
    client: ApiClient, caplog: pytest.LogCaptureFixture
) -> None:
    sensitive_path = "/nicht-vorhanden-83.456"
    with caplog.at_level(logging.INFO):
        response = client.get(sensitive_path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    request_log = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "nutrition_companion.request"
    )
    assert sensitive_path not in request_log
    assert '"endpoint":"/{unmatched}"' in request_log


def test_unexpected_exception_is_sanitized_before_server_logging(
    client: ApiClient,
    complete_profile_payload: dict[str, object],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_token = "sensitive-database-value-83.456"

    def fail_update(*_args: object, **_kwargs: object) -> NoReturn:
        raise RuntimeError(sensitive_token)

    monkeypatch.setattr(profile_service, "update_profile", fail_update)
    with caplog.at_level(logging.INFO):
        response = client.put("/api/v1/profile", json=complete_profile_payload)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert sensitive_token not in response.text
    assert sensitive_token not in caplog.text


def test_non_local_configuration_rejects_insecure_runtime() -> None:
    try:
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://runtime:secret@db.internal/app",
            public_api_url="http://api.example.test",
            allow_insecure_local_http=True,
            use_development_profile_resolver=True,
            cors_origins="*",
        )
    except ValueError as error:
        assert "HTTPS" in str(error)
    else:
        raise AssertionError("unsafe production settings were accepted")


def test_non_local_configuration_rejects_development_resolver() -> None:
    try:
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://runtime:secret@db.internal/app",
            public_api_url="https://api.example.test",
            allow_insecure_local_http=False,
            use_development_profile_resolver=True,
            cors_origins="https://app.example.test",
        )
    except ValueError as error:
        assert "development profile resolver" in str(error)
    else:
        raise AssertionError("development resolver was accepted in production")


def test_request_logs_exclude_sensitive_values(
    client: ApiClient,
    complete_profile_payload: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_weight = "83.456789"
    complete_profile_payload["current_weight_kg"] = sensitive_weight
    with caplog.at_level(logging.INFO):
        response = client.put("/api/v1/profile", json=complete_profile_payload)
    assert response.status_code == 200
    log_text = caplog.text
    assert sensitive_weight not in log_text
    assert "1990-06-15" not in log_text
    assert "body_fat_percentage" not in log_text
