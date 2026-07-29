from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.nutrition_assessment import repository as assessment_repository
from app.modules.nutrition_assessment.models import Assessment
from app.modules.recipe_target_comparison.engine import RecipeNutrientInput, compare_item
from app.modules.recipe_target_comparison.schemas import (
    ComparableAssessment,
    ComparableAssessmentsResponse,
    TargetComparisonResponse,
)
from app.modules.recipe_target_comparison.target_extraction import extract_targets, is_usable
from app.modules.recipes import service as recipe_service
from app.modules.recipes.engine.calculation import calculate_recipe

GROUPS = {
    "energy": ("Energie", {"energy"}),
    "macronutrients": ("Energie und Makronährstoffe", {"macronutrient"}),
    "additional": (
        "Ballaststoffe und weitere Werte",
        {"fiber", "fat_detail", "carbohydrate_detail"},
    ),
    "vitamins": ("Vitamine", {"vitamin"}),
    "minerals": ("Mineralstoffe", {"mineral"}),
}


def comparable_assessments(session: Session, profile_id: UUID) -> ComparableAssessmentsResponse:
    detailed = assessment_repository.list_assessments_with_metrics(session, profile_id)
    items: list[ComparableAssessment] = []
    latest: UUID | None = None
    for assessment in detailed:
        assert assessment is not None
        usable = is_usable(assessment)
        if usable and latest is None:
            latest = assessment.id
        energy = assessment.summary.get("energy_target")
        energy_label = None
        if isinstance(energy, dict) and energy.get("available"):
            energy_label = (
                f"{energy.get('lower')} bis {energy.get('upper')} {energy.get('unit', 'kcal/Tag')}"
            )
        items.append(
            ComparableAssessment(
                id=assessment.id,
                calculated_at=assessment.calculated_at,
                goal_type=str(assessment.summary.get("goal_type", "unknown")),
                supported_scope_status=assessment.supported_scope_status,
                energy_target_summary=energy_label,
                reference_set_version=assessment.reference_set_version,
                usable_for_comparison=usable,
                unavailable_reason_de=None
                if usable
                else "Nicht für einen Rezeptvergleich geeignet",
            )
        )
    return ComparableAssessmentsResponse(items=items, latest_usable_assessment_id=latest)


def compare(
    session: Session,
    profile_id: UUID,
    recipe_id: UUID,
    assessment_id: UUID | None,
    portion_count: Decimal,
) -> TargetComparisonResponse:
    if not portion_count.is_finite() or portion_count <= 0 or portion_count > 100:
        raise ApiError(
            code="INVALID_PORTION_COUNT",
            message="Die Portionszahl muss größer als null und höchstens 100 sein.",
            status_code=422,
        )
    recipe = recipe_service.require(session, profile_id, recipe_id)
    assessment = _resolve_assessment(session, profile_id, assessment_id)
    targets = extract_targets(assessment)
    calculation = calculate_recipe(recipe)
    recipe_values = {
        str(item["nutrient_code"]): RecipeNutrientInput(
            nutrient_code=str(item["nutrient_code"]),
            amount_per_serving=Decimal(item["amount_per_serving"]),
            unit=str(item["unit"]),
            coverage_ratio=Decimal(item["coverage_ratio"]),
            known_ingredient_count=int(item["known_ingredient_count"]),
            relevant_ingredient_count=int(item["relevant_ingredient_count"]),
            missing_ingredients=tuple(item["missing_ingredients"]),
            is_complete=bool(item["is_complete"]),
        )
        for item in calculation["nutrients"]
    }
    grouped: dict[str, list[dict[str, object]]] = {code: [] for code in GROUPS}
    flat: list[dict[str, object]] = []
    for target in targets:
        item = compare_item(recipe_values.get(target.nutrient_code), target, portion_count)
        flat.append(item)
        group = next(
            (code for code, (_, categories) in GROUPS.items() if target.category in categories),
            "additional",
        )
        grouped[group].append(item)
    groups = [
        {"code": code, "display_name_de": label, "items": grouped[code]}
        for code, (label, _) in GROUPS.items()
        if grouped[code]
    ]
    status_counts = {
        status: sum(item["comparison_status"] == status for item in flat)
        for status in ("complete", "partial", "unavailable")
    }
    notices = [
        "Der Vergleich nutzt die unveränderten Zielwerte des gewählten Assessments und "
        "die aktuellen Nährwertdaten des Rezepts.",
        "Der Vergleich betrachtet nur die gewählte Rezeptmenge, nicht die gesamte Tagesernährung.",
    ]
    if recipe.is_archived:
        notices.append("Das archivierte Rezept wird schreibgeschützt verglichen.")
    return TargetComparisonResponse.model_validate(
        {
            "recipe": {
                "id": recipe.id,
                "name": recipe.name,
                "updated_at": recipe.updated_at,
                "base_servings": recipe.servings,
            },
            "assessment": {
                "id": assessment.id,
                "calculated_at": assessment.calculated_at,
                "goal_type": assessment.summary.get("goal_type", "unknown"),
                "reference_set_version": assessment.reference_set_version,
                "application_rule_set_version": assessment.application_rule_set_version,
            },
            "portion_count": portion_count,
            "calculated_at": datetime.now(UTC),
            "groups": groups,
            "summary": {
                "comparable_target_count": len(flat),
                "complete_comparison_count": status_counts["complete"],
                "partial_comparison_count": status_counts["partial"],
                "unavailable_comparison_count": status_counts["unavailable"],
                "has_incomplete_basic_nutrition": not bool(
                    calculation["quality"]["basic_nutrition_complete"]
                ),
                "has_exceeded_maximum": any(item["relation"] == "exceeds_limit" for item in flat),
            },
            "notices": notices,
        }
    )


def _resolve_assessment(
    session: Session, profile_id: UUID, assessment_id: UUID | None
) -> Assessment:
    if assessment_id is not None:
        assessment = assessment_repository.get_assessment(session, profile_id, assessment_id)
        if assessment is None:
            raise ApiError(
                code="ASSESSMENT_NOT_FOUND",
                message="Die ausgewählte Einschätzung wurde nicht gefunden.",
                status_code=404,
            )
        if not is_usable(assessment):
            raise ApiError(
                code="ASSESSMENT_NOT_COMPARABLE",
                message="Diese Einschätzung enthält keine geeigneten Zielwerte.",
                status_code=409,
            )
        return assessment
    assessments = assessment_repository.list_assessments_with_metrics(session, profile_id)
    for candidate in assessments:
        if is_usable(candidate):
            return candidate
    raise ApiError(
        code="NO_USABLE_ASSESSMENT",
        message="Für den persönlichen Vergleich benötigst du zuerst eine Ernährungsanalyse.",
        status_code=404,
    )
