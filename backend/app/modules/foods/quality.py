from app.modules.foods.nutrient_catalog import CORE_CODES, NUTRIENT_BY_CODE


def calculate_quality(
    known_codes: set[str], derived_codes: set[str], estimated_measures: int
) -> dict[str, object]:
    missing = sorted(CORE_CODES - known_codes)
    micronutrients = sum(
        1
        for code in known_codes
        if NUTRIENT_BY_CODE[code].category in {"vitamin", "mineral"}
        and code not in {"salt", "sodium"}
    )
    level = (
        "incomplete"
        if missing
        else ("extended" if len(known_codes - CORE_CODES) >= 4 else "basic_complete")
    )
    warnings = ["Grundnährwerte sind unvollständig."] if missing else []
    return {
        "basic_nutrition_complete": not missing,
        "known_nutrient_count": len(known_codes | derived_codes),
        "available_micronutrient_count": micronutrients,
        "missing_basic_nutrients": missing,
        "derived_nutrients": sorted(derived_codes),
        "estimated_measure_count": estimated_measures,
        "quality_level": level,
        "warnings": warnings,
    }
