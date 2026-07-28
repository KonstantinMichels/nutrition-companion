from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.database.session import get_db
from app.modules.reference_data import repository
from app.modules.reference_data.schemas import CurrentReferenceSetsResponse

router = APIRouter(prefix="/api/v1/reference-sets", tags=["reference data"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/current", response_model=CurrentReferenceSetsResponse)
def read_current_reference_sets(session: DbSession) -> object:
    reference_set = repository.current_reference_set(session)
    rule_set = repository.current_application_rule_set(session)
    if reference_set is None or rule_set is None:
        raise ApiError(
            code="REFERENCE_DATA_NOT_SEEDED",
            message="Die Referenzdaten sind noch nicht initialisiert.",
            status_code=503,
        )
    return {
        "reference_set_identifier": reference_set.identifier,
        "reference_set_version": reference_set.version,
        "source_organization": reference_set.source_organization,
        "edition": reference_set.edition,
        "publication_date": reference_set.publication_date,
        "effective_date": reference_set.effective_date,
        "application_rule_set_identifier": rule_set.identifier,
        "application_rule_set_version": rule_set.version,
        "application_rule_set_effective_date": rule_set.effective_date,
        "metadata": {
            "reference_set": reference_set.metadata_json,
            "application_rule_set": rule_set.metadata_json,
        },
    }
