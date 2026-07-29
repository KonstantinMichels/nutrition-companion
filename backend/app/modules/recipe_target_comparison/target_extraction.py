from app.modules.foods.nutrient_catalog import NUTRIENT_BY_CODE
from app.modules.nutrition_assessment.models import Assessment
from app.modules.recipe_target_comparison.engine import TargetDescriptor
from app.modules.recipe_target_comparison.target_mapping import mapping_for


def extract_targets(assessment: Assessment) -> list[TargetDescriptor]:
    targets: list[TargetDescriptor] = []
    for metric in assessment.metrics:
        mapping = mapping_for(metric.metric_code)
        definition = NUTRIENT_BY_CODE.get(mapping.nutrient_code) if mapping else None
        if mapping is None or definition is None or metric.raw_value is None:
            continue
        minimum, maximum = metric.lower_value, metric.upper_value
        if mapping.target_kind == "range":
            minimum = minimum or metric.raw_value
            maximum = maximum or metric.raw_value
        elif mapping.target_kind == "minimum":
            minimum = minimum or metric.raw_value
        elif mapping.target_kind == "maximum":
            maximum = metric.raw_value
        targets.append(
            TargetDescriptor(
                nutrient_code=mapping.nutrient_code,
                display_name_de=definition.display_name_de,
                target_kind=mapping.target_kind,
                value=metric.raw_value,
                minimum=minimum,
                maximum=maximum,
                unit=metric.unit,
                category=definition.category,
                display_order=definition.display_order,
            )
        )
    return sorted(targets, key=lambda item: item.display_order)


def is_usable(assessment: Assessment) -> bool:
    return assessment.supported_scope_status == "supported" and bool(extract_targets(assessment))
