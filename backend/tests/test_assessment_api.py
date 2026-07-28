from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.branding import CONSENT_TEXT_VERSION
from app.core.config import get_settings
from app.modules.nutrition_assessment import service as assessment_service
from app.modules.nutrition_assessment.models import Assessment
from app.modules.privacy import service as privacy_service
from app.modules.privacy.models import ConsentRecord
from app.modules.profiles.models import Profile
from app.modules.reference_data.models import ReferenceSet
from tests.conftest import ApiClient


def _grant_consent(client: ApiClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/privacy/consents",
        json={
            "purpose_code": "nutrition_assessment_calculation",
            "consent_text_version": CONSENT_TEXT_VERSION,
            "affirmed": True,
            "source": "android_onboarding",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_assessment(client: ApiClient, request_id: str | None = None) -> object:
    return client.post(
        "/api/v1/assessments",
        json={"client_request_id": request_id or str(uuid4())},
    )


def test_assessment_requires_current_consent(
    client: ApiClient, seeded_database: None, saved_profile: None, db_session: Session
) -> None:
    response = _create_assessment(client)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CONSENT_REQUIRED"

    profile_id = get_settings().development_profile_id
    db_session.add(
        ConsentRecord(
            profile_id=profile_id,
            purpose_code="nutrition_assessment_calculation",
            consent_text_version="obsolete_consent_version",
            status="granted",
            granted_at=datetime(2026, 7, 1, tzinfo=UTC),
            source="android_onboarding",
        )
    )
    db_session.commit()
    obsolete_response = _create_assessment(client)
    assert obsolete_response.status_code == 403
    assert obsolete_response.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_assessment_creation_persistence_history_and_idempotency(
    client: ApiClient, seeded_database: None, saved_profile: None, db_session: Session
) -> None:
    _grant_consent(client)
    request_id = str(uuid4())
    created = _create_assessment(client, request_id)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["supported_scope_status"] == "supported"
    assert body["reference_set_identifier"] == "dge_oege_v3_mvp_2026_05"
    assert body["reference_set_version"] == ("3rd-edition-2025_erratum-2026-05_subset-v1")
    assert body["application_rule_set_identifier"] == "nutrition_companion_mvp_v1"
    assert body["application_rule_set_version"] == "v1"
    assert body["engine_version"] == "nutrition_engine_v1"
    metric_codes = {item["metric_code"] for item in body["metrics"]}
    assert {
        "anthropometrics.bmi",
        "energy.resting_energy",
        "activity.pal",
        "energy.maintenance",
        "energy.goal_target",
        "protein.grams_per_day",
        "macros.fat_grams",
        "macros.carbohydrate_grams",
        "fiber.target",
        "hydration.total_water",
    }.issubset(metric_codes)
    bmi = next(item for item in body["metrics"] if item["metric_code"] == "anthropometrics.bmi")
    manually_calculated_bmi = Decimal("82.5") / (Decimal("1.8") ** 2)
    assert abs(Decimal(bmi["raw_value"]) - manually_calculated_bmi) < Decimal("1e-14")
    assert bmi["source_metadata"]["reference_set_identifier"] == ("dge_oege_v3_mvp_2026_05")
    assert body["summary"]["food_groups"]
    assert [item["metric_code"] for item in body["metrics"]] == sorted(metric_codes)

    stored = db_session.scalar(select(Assessment).where(Assessment.id == UUID(body["id"])))
    assert stored is not None
    engine_input = stored.input_snapshot["engine_input"]
    energy_target = stored.summary["energy_target"]
    assert isinstance(engine_input, dict)
    assert isinstance(energy_target, dict)
    assert isinstance(engine_input["weight_kg"], str)
    assert Decimal(engine_input["weight_kg"]) == Decimal("82.5")
    assert isinstance(energy_target["midpoint"], str)

    duplicate = _create_assessment(client, request_id)
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == body["id"]
    count = db_session.scalar(select(func.count()).select_from(Assessment))
    assert count == 1

    latest = client.get("/api/v1/assessments/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == body["id"]
    detail = client.get(f"/api/v1/assessments/{body['id']}")
    assert detail.status_code == 200
    history = client.get("/api/v1/assessments?limit=10&offset=0")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["goal_type"] == "lose_weight"


def test_old_assessment_is_immutable_after_profile_edit(
    client: ApiClient,
    seeded_database: None,
    saved_profile: None,
    complete_profile_payload: dict[str, object],
) -> None:
    _grant_consent(client)
    first = _create_assessment(client).json()
    first_bmi = next(
        metric for metric in first["metrics"] if metric["metric_code"] == "anthropometrics.bmi"
    )["raw_value"]

    changed = deepcopy(complete_profile_payload)
    changed["current_weight_kg"] = "92,5"
    assert client.put("/api/v1/profile", json=changed).status_code == 200
    old_again = client.get(f"/api/v1/assessments/{first['id']}").json()
    old_bmi = next(
        metric for metric in old_again["metrics"] if metric["metric_code"] == "anthropometrics.bmi"
    )["raw_value"]
    assert Decimal(old_bmi) == Decimal(first_bmi)

    second = _create_assessment(client).json()
    second_bmi = next(
        metric for metric in second["metrics"] if metric["metric_code"] == "anthropometrics.bmi"
    )["raw_value"]
    assert Decimal(second_bmi) > Decimal(first_bmi)
    assert second["id"] != first["id"]


def test_withdrawn_consent_blocks_only_new_assessments(
    client: ApiClient, seeded_database: None, saved_profile: None
) -> None:
    consent = _grant_consent(client)
    request_id = str(uuid4())
    original = _create_assessment(client, request_id).json()
    withdrawn = client.post(f"/api/v1/privacy/consents/{consent['id']}/withdraw")
    assert withdrawn.status_code == 200

    exact_retry = _create_assessment(client, request_id)
    assert exact_retry.status_code == 201
    assert exact_retry.json()["id"] == original["id"]

    blocked = _create_assessment(client)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "CONSENT_REQUIRED"
    assert client.get(f"/api/v1/assessments/{original['id']}").status_code == 200


def test_unsupported_scope_returns_flags_without_goal_or_high_protein_target(
    client: ApiClient, seeded_database: None, saved_profile: None
) -> None:
    screening = {
        "pregnant": False,
        "breastfeeding": False,
        "diagnosed_eating_disorder": False,
        "diabetes": False,
        "kidney_disease": True,
        "liver_disease": False,
        "medically_prescribed_diet": False,
        "serious_metabolic_condition": False,
        "other_professional_nutrition_condition": False,
    }
    assert client.put("/api/v1/profile/health-screening", json=screening).status_code == 200
    _grant_consent(client)
    response = _create_assessment(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["supported_scope_status"] == "unsupported"
    codes = {flag["code"] for flag in body["safety_flags"]}
    assert "UNSUPPORTED_KIDNEY_DISEASE" in codes
    goal = next(
        metric for metric in body["metrics"] if metric["metric_code"] == "energy.goal_target"
    )
    protein = next(
        metric for metric in body["metrics"] if metric["metric_code"] == "protein.grams_per_day"
    )
    assert goal["raw_value"] is None
    # The general 0.8 g/kg reference may still be displayed, but no athletic
    # high-protein target is generated for this unsupported medical case.
    assert Decimal(protein["raw_value"]) == Decimal("66")
    assert protein["upper_value"] is None
    assert protein["application_rule_identifier"] == (
        "nutrition_companion_mvp_v1:general_protein_reference_no_athletic_increase"
    )


def test_export_and_assessment_history_hard_deletion(
    client: ApiClient, seeded_database: None, saved_profile: None
) -> None:
    _grant_consent(client)
    assessment_id = _create_assessment(client).json()["id"]
    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200
    assert exported.json()["data"]["assessments"][0]["id"] == assessment_id
    exported_metrics = exported.json()["data"]["assessments"][0]["metrics"]
    bmi = next(item for item in exported_metrics if item["metric_code"] == "anthropometrics.bmi")
    assert isinstance(bmi["raw_value"], str)
    assert Decimal(bmi["raw_value"]) == Decimal("25.462962962962962")

    deleted = client.request("DELETE", "/api/v1/assessments", json={"confirm": True})
    assert deleted.status_code == 200
    assert deleted.json()["scope"] == "assessment_history"
    assert client.get(f"/api/v1/assessments/{assessment_id}").status_code == 404
    assert client.get("/api/v1/profile").status_code == 200


def test_assessment_transaction_rolls_back_on_commit_failure(
    client: ApiClient,
    seeded_database: None,
    saved_profile: None,
    session_factory: sessionmaker[Session],
) -> None:
    _grant_consent(client)
    profile_id = get_settings().development_profile_id
    with session_factory() as transaction_session:

        def fail_commit(_session: Session) -> None:
            raise RuntimeError("simulated commit failure")

        event.listen(transaction_session, "before_commit", fail_commit, once=True)
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            assessment_service.create_assessment(
                transaction_session,
                profile_id,
                uuid4(),
            )
        assert not transaction_session.new

    with session_factory() as verification_session:
        count = verification_session.scalar(select(func.count()).select_from(Assessment))
        assert count == 0


def test_complete_profile_deletion_cascades_assessment_and_consent(
    client: ApiClient,
    seeded_database: None,
    saved_profile: None,
    db_session: Session,
) -> None:
    _grant_consent(client)
    assert _create_assessment(client).status_code == 201
    deleted = client.request("DELETE", "/api/v1/profile", json={"confirm": True})
    assert deleted.status_code == 200
    assert db_session.scalar(select(func.count()).select_from(Profile)) == 0
    assert db_session.scalar(select(func.count()).select_from(Assessment)) == 0
    assert db_session.scalar(select(func.count()).select_from(ConsentRecord)) == 0


def test_complete_deletion_rolls_back_as_one_transaction(
    client: ApiClient,
    seeded_database: None,
    saved_profile: None,
    session_factory: sessionmaker[Session],
) -> None:
    _grant_consent(client)
    assert _create_assessment(client).status_code == 201
    profile_id = get_settings().development_profile_id
    with session_factory() as transaction_session:

        def fail_commit(_session: Session) -> None:
            raise RuntimeError("simulated deletion failure")

        event.listen(transaction_session, "before_commit", fail_commit, once=True)
        with pytest.raises(RuntimeError, match="simulated deletion failure"):
            privacy_service.delete_complete_profile(transaction_session, profile_id)

    with session_factory() as verification_session:
        assert verification_session.get(Profile, profile_id) is not None
        assert verification_session.scalar(select(func.count()).select_from(Assessment)) == 1


def test_current_reference_endpoint_reports_seeded_versions(
    client: ApiClient, seeded_database: None
) -> None:
    response = client.get("/api/v1/reference-sets/current")
    assert response.status_code == 200
    body = response.json()
    assert body["reference_set_identifier"] == "dge_oege_v3_mvp_2026_05"
    assert body["application_rule_set_identifier"] == "nutrition_companion_mvp_v1"
    assert body["metadata"]["reference_set"]["is_complete"] is False


def test_reference_version_mismatch_fails_closed_without_persistence(
    client: ApiClient,
    seeded_database: None,
    saved_profile: None,
    db_session: Session,
) -> None:
    _grant_consent(client)
    reference_set = db_session.scalar(select(ReferenceSet))
    assert reference_set is not None
    reference_set.version = "unexpected-database-version"
    db_session.commit()

    response = _create_assessment(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REFERENCE_VERSION_MISMATCH"
    assert db_session.scalar(select(func.count()).select_from(Assessment)) == 0
