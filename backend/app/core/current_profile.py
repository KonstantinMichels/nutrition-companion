from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.config import get_settings
from app.core.errors import ApiError


async def resolve_current_profile_id() -> UUID:
    """Development-only identity boundary; this is explicitly not authentication."""

    settings = get_settings()
    if not settings.use_development_profile_resolver:
        raise ApiError(
            code="AUTHENTICATION_NOT_CONFIGURED",
            message="Für diese Umgebung ist noch keine Anmeldung konfiguriert.",
            status_code=503,
        )
    if not settings.is_local:
        # Defense in depth in addition to the settings validator.
        raise ApiError(
            code="DEVELOPMENT_RESOLVER_FORBIDDEN",
            message="Die Entwicklungsidentität ist in dieser Umgebung nicht zulässig.",
            status_code=503,
        )
    return settings.development_profile_id


CurrentProfileId = Annotated[UUID, Depends(resolve_current_profile_id)]
