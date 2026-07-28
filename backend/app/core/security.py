"""Security invariants shared by startup and tests."""

from app.core.config import Settings


def assert_safe_runtime_configuration(settings: Settings) -> None:
    # Instantiating Settings already runs the complete fail-closed validation.
    # Keeping this named boundary makes the startup security decision explicit.
    if not settings.is_local and settings.public_api_url.scheme != "https":
        raise RuntimeError("HTTPS is required outside local development")
