from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request, Response

from app.core.errors import ApiError, api_error_response


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format="%(message)s")


def _safe_endpoint(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if isinstance(template, str):
        return template
    return "/{unmatched}"


async def request_log_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = uuid4().hex[:16]
    request.state.request_id = request_id
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        # Starlette re-raises exceptions after its 500 handler, allowing Uvicorn
        # to log exception text that may contain submitted or database values.
        # Terminate the exception at this outer boundary without serializing it.
        status = 500
        response = api_error_response(
            request,
            ApiError(
                code="INTERNAL_ERROR",
                message="Ein technischer Fehler ist aufgetreten.",
                status_code=500,
            ),
        )
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logging.getLogger("nutrition_companion.request").info(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "request_id": request_id,
                    "endpoint": _safe_endpoint(request),
                    "method": request.method,
                    "status": status,
                    "duration_ms": duration_ms,
                },
                separators=(",", ":"),
            )
        )
