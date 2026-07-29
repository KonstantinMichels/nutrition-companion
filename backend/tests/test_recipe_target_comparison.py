from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.branding import CONSENT_TEXT_VERSION
from app.modules.recipe_target_comparison.engine import (
    RecipeNutrientInput,
    TargetDescriptor,
    compare_item,
)
from app.modules.recipe_target_comparison.unit_conversion import (
    IncompatibleUnitError,
    convert,
)
from tests.test_recipe_core import create_food, recipe_payload


def nutrient(*, complete: bool = True, amount: str = "25", unit: str = "g"):
    return RecipeNutrientInput(
        nutrient_code="protein",
        amount_per_serving=Decimal(amount),
        unit=unit,
        coverage_ratio=Decimal(1 if complete else "0.5"),
        known_ingredient_count=2 if complete else 1,
        relevant_ingredient_count=2,
        missing_ingredients=() if complete else ({"food_name": "Unbekannt"},),
        is_complete=complete,
    )


def target(kind, *, value="100", minimum=None, maximum=None, unit="g/Tag"):
    return TargetDescriptor(
        nutrient_code="protein",
        display_name_de="Eiweiß",
        target_kind=kind,
        value=None if value is None else Decimal(value),
        minimum=None if minimum is None else Decimal(minimum),
        maximum=None if maximum is None else Decimal(maximum),
        unit=unit,
        category="macronutrient",
        display_order=1,
    )


def test_decimal_unit_conversion_is_exact():
    assert convert(Decimal("0.012"), "g", "mg") == Decimal(12)
    assert convert(Decimal(500), "µg", "mg") == Decimal("0.5")
    assert convert(Decimal(100), "kcal", "kJ") == Decimal("418.4")
    assert convert(Decimal("418.4"), "kJ", "kcal") == Decimal(100)
    with pytest.raises(IncompatibleUnitError):
        convert(Decimal(1), "g", "ml")


def test_target_kinds_and_incomplete_semantics():
    minimum = compare_item(nutrient(), target("minimum", minimum="100"), Decimal(1))
    assert minimum["contribution_percent"] == Decimal(25)
    assert minimum["relation"] == "contribution"
    maximum = compare_item(nutrient(), target("maximum", maximum="20"), Decimal(1))
    assert maximum["relation"] == "exceeds_limit"
    assert "Tageshöchstwert" in str(maximum["explanation"])
    ranged = compare_item(
        nutrient(), target("range", value="125", minimum="100", maximum="150"), Decimal(2)
    )
    assert ranged["relation"] == "below_range"
    partial_max = compare_item(
        nutrient(complete=False, amount="5"), target("maximum", maximum="20"), Decimal(1)
    )
    assert partial_max["relation"] == "unknown_due_to_incomplete_data"
    unavailable = compare_item(None, target("reference"), Decimal(1))
    assert unavailable["selected_amount"] is None
    assert unavailable["contribution_percent"] is None


def _create_assessment(client):
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
    response = client.post("/api/v1/assessments", json={"client_request_id": str(uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


def test_api_latest_explicit_portions_archived_and_metadata(client, seeded_database, saved_profile):
    assessment = _create_assessment(client)
    food = create_food(client)
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    default = client.get(f"/api/v1/recipes/{recipe['id']}/target-comparison")
    assert default.status_code == 200, default.text
    body = default.json()
    assert body["assessment"]["id"] == assessment["id"]
    assert body["portion_count"] == "1"
    protein = next(
        item
        for group in body["groups"]
        for item in group["items"]
        if item["nutrient_code"] == "protein"
    )
    half = client.get(
        f"/api/v1/recipes/{recipe['id']}/target-comparison"
        f"?assessment_id={assessment['id']}&portion_count=0.5"
    ).json()
    half_protein = next(
        item
        for group in half["groups"]
        for item in group["items"]
        if item["nutrient_code"] == "protein"
    )
    assert Decimal(half_protein["selected_amount"]) == Decimal(protein["selected_amount"]) / 2
    client.delete(f"/api/v1/recipes/{recipe['id']}")
    archived = client.get(f"/api/v1/recipes/{recipe['id']}/target-comparison")
    assert archived.status_code == 200
    assert any("archivierte" in notice for notice in archived.json()["notices"])
    comparable = client.get("/api/v1/assessments/comparable")
    assert comparable.status_code == 200
    assert comparable.json()["latest_usable_assessment_id"] == assessment["id"]


def test_api_empty_and_invalid_states(client, saved_profile):
    food = create_food(client)
    recipe = client.post("/api/v1/recipes", json=recipe_payload(food["id"])).json()
    missing = client.get(f"/api/v1/recipes/{recipe['id']}/target-comparison")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NO_USABLE_ASSESSMENT"
    assert (
        client.get(f"/api/v1/recipes/{recipe['id']}/target-comparison?portion_count=0").status_code
        == 422
    )
