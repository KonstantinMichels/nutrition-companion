from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


class CurrentReferenceSetsResponse(BaseModel):
    reference_set_identifier: str
    reference_set_version: str
    source_organization: str
    edition: str
    publication_date: date | None
    effective_date: date
    application_rule_set_identifier: str
    application_rule_set_version: str
    application_rule_set_effective_date: date
    metadata: dict[str, Any]
