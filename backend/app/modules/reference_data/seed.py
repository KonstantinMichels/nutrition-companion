from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.database.models  # noqa: F401  # register the complete relationship graph
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.modules.privacy.models import ProcessingPurpose
from app.modules.privacy.registry import (
    PROCESSING_PURPOSE_REGISTRY_VERSION,
    PROCESSING_PURPOSES,
)
from app.modules.reference_data.models import ApplicationRuleSet, ReferenceSet, ReferenceValue
from app.seed.loader import (
    load_application_rules_document,
    load_food_groups_document,
    load_reference_values_document,
)


def _required_mapping(document: dict[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"seed field {key!r} must be an object")
    return value


def _required_list(document: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = document.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"seed field {key!r} must be a list of objects")
    return value


def seed_processing_purposes(session: Session) -> int:
    inserted_or_updated = 0
    for item in PROCESSING_PURPOSES:
        existing = session.get(ProcessingPurpose, item["code"])
        values = {**item, "registry_version": PROCESSING_PURPOSE_REGISTRY_VERSION}
        if existing is None:
            session.add(ProcessingPurpose(**values))
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        inserted_or_updated += 1
    return inserted_or_updated


def seed_scientific_reference_data(session: Session) -> tuple[ReferenceSet, int]:
    document = load_reference_values_document()
    metadata = _required_mapping(document, "reference_set")
    sources = _required_mapping(document, "sources")
    nutrient_catalog = _required_list(document, "nutrient_catalog")
    micronutrients = _required_list(document, "micronutrient_values")
    hydration_values = _required_list(document, "hydration_values")

    identifier = str(metadata["identifier"])
    version = str(metadata["version"])
    existing = session.scalar(
        select(ReferenceSet).where(
            ReferenceSet.identifier == identifier,
            ReferenceSet.version == version,
        )
    )
    if existing is not None:
        return existing, 0

    reference_set = ReferenceSet(
        identifier=identifier,
        source_organization=str(metadata["source_organization"]),
        edition=str(metadata["edition"]),
        version=version,
        publication_date=(
            date.fromisoformat(str(metadata["publication_date"]))
            if metadata.get("publication_date")
            else None
        ),
        effective_date=date.fromisoformat(str(metadata["effective_date"])),
        metadata_json={
            "verified_on": metadata.get("verified_on"),
            "is_complete": metadata.get("is_complete", False),
            "completeness_note_de": metadata.get("completeness_note_de"),
            "sources": sources,
            "hydration_values": hydration_values,
            "nutrient_catalog": nutrient_catalog,
        },
    )
    session.add(reference_set)
    session.flush()

    catalog_by_code = {str(item["code"]): item for item in nutrient_catalog}
    inserted = 0
    for item in micronutrients:
        nutrient_code = str(item["nutrient_code"])
        catalog = catalog_by_code.get(nutrient_code)
        if catalog is None:
            raise ValueError(f"missing nutrient catalog entry for {nutrient_code}")
        source_identifier = str(item["source_identifier"])
        source = sources.get(source_identifier)
        if not isinstance(source, dict) or not source.get("url"):
            raise ValueError(f"missing official source URL for {source_identifier}")
        source_note_parts = [
            str(source.get("title", "")),
            str(source.get("edition", "")),
            str(item.get("source_note", "")),
        ]
        session.add(
            ReferenceValue(
                reference_set_id=reference_set.id,
                nutrient_code=nutrient_code,
                display_name_de=str(catalog["display_name_de"]),
                physiological_category=item.get("physiological_category"),
                age_min_years=item.get("age_min_years"),
                age_max_years_exclusive=item.get("age_max_years_exclusive"),
                pregnancy_state=str(item.get("pregnancy_state", "not_pregnant")),
                breastfeeding_state=str(item.get("breastfeeding_state", "not_breastfeeding")),
                value=Decimal(str(item["value"])) if item.get("value") is not None else None,
                lower_value=(
                    Decimal(str(item["lower_value"]))
                    if item.get("lower_value") is not None
                    else None
                ),
                upper_value=(
                    Decimal(str(item["upper_value"]))
                    if item.get("upper_value") is not None
                    else None
                ),
                unit=str(item.get("unit", catalog["unit"])),
                reference_value_category=str(item["reference_value_category"]),
                source_note=" — ".join(part for part in source_note_parts if part),
                source_url=str(source["url"]),
                superseded_date=(
                    date.fromisoformat(str(item["superseded_date"]))
                    if item.get("superseded_date")
                    else None
                ),
            )
        )
        inserted += 1
    return reference_set, inserted


def seed_application_rules(session: Session) -> tuple[ApplicationRuleSet, bool]:
    document = load_application_rules_document()
    food_groups = load_food_groups_document()
    metadata = _required_mapping(document, "rule_set")
    identifier = str(metadata["identifier"])
    version = str(metadata["version"])
    existing = session.scalar(
        select(ApplicationRuleSet).where(
            ApplicationRuleSet.identifier == identifier,
            ApplicationRuleSet.version == version,
        )
    )
    if existing is not None:
        return existing, False
    rule_set = ApplicationRuleSet(
        identifier=identifier,
        name=str(metadata["name"]),
        version=version,
        effective_date=date.fromisoformat(str(metadata["effective_date"])),
        metadata_json={"application_rules": document, "food_groups": food_groups},
    )
    session.add(rule_set)
    return rule_set, True


def seed_all(session: Session) -> dict[str, int]:
    try:
        purposes = seed_processing_purposes(session)
        _reference_set, reference_values = seed_scientific_reference_data(session)
        _rule_set, rule_inserted = seed_application_rules(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "processing_purposes": purposes,
        "reference_values_inserted": reference_values,
        "application_rule_sets_inserted": int(rule_inserted),
    }


def main() -> None:
    # Resolve settings before opening a database connection so unsafe non-local
    # configurations fail closed in the same way as API startup.
    get_settings()
    with SessionLocal() as session:
        counts = seed_all(session)
    print(
        "Seed complete: "
        f"{counts['processing_purposes']} purposes processed, "
        f"{counts['reference_values_inserted']} reference values inserted, "
        f"{counts['application_rule_sets_inserted']} rule set inserted."
    )


if __name__ == "__main__":
    main()
