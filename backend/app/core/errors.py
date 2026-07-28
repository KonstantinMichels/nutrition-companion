from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@dataclass(slots=True)
class ApiError(Exception):
    code: str
    message: str
    status_code: int
    field_errors: list[dict[str, str]] = field(default_factory=list)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def api_error_response(request: Request, error: ApiError) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": error.code,
            "message": error.message,
            "field_errors": error.field_errors,
        },
        "request_id": _request_id(request),
    }
    return JSONResponse(status_code=error.status_code, content=body)


async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
    return api_error_response(request, error)


_TYPE_MESSAGES = {
    "missing": ("REQUIRED", "Dieses Feld ist erforderlich."),
    "greater_than": ("OUT_OF_RANGE", "Bitte gib einen plausiblen Wert ein."),
    "greater_than_equal": ("OUT_OF_RANGE", "Bitte gib einen plausiblen Wert ein."),
    "less_than": ("OUT_OF_RANGE", "Bitte gib einen plausiblen Wert ein."),
    "less_than_equal": ("OUT_OF_RANGE", "Bitte gib einen plausiblen Wert ein."),
    "decimal_parsing": ("INVALID_DECIMAL", "Bitte gib eine gültige Zahl ein."),
    "float_parsing": ("INVALID_DECIMAL", "Bitte gib eine gültige Zahl ein."),
    "date_from_datetime_parsing": ("INVALID_DATE", "Bitte gib ein gültiges Datum ein."),
}


async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    field_errors: list[dict[str, str]] = []
    for item in error.errors():
        location = [str(part) for part in item.get("loc", ()) if part not in {"body", "query"}]
        error_type = str(item.get("type", "validation_error"))
        code, message = _TYPE_MESSAGES.get(
            error_type,
            ("INVALID_VALUE", "Bitte prüfe diese Eingabe."),
        )
        field_errors.append(
            {
                "field": ".".join(location) or "request",
                "code": code,
                "message": message,
            }
        )
    return api_error_response(
        request,
        ApiError(
            code="VALIDATION_ERROR",
            message="Die Eingaben konnten nicht verarbeitet werden.",
            status_code=422,
            field_errors=field_errors,
        ),
    )


async def http_error_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
    code, message = {
        404: ("NOT_FOUND", "Die angeforderte Ressource wurde nicht gefunden."),
        405: ("METHOD_NOT_ALLOWED", "Diese HTTP-Methode ist für die Ressource nicht erlaubt."),
    }.get(
        error.status_code,
        ("HTTP_ERROR", "Die Anfrage konnte nicht verarbeitet werden."),
    )
    return api_error_response(
        request,
        ApiError(code=code, message=message, status_code=error.status_code),
    )


async def unexpected_error_handler(request: Request, _error: Exception) -> JSONResponse:
    # Deliberately do not serialize the exception: it may contain submitted values.
    return api_error_response(
        request,
        ApiError(
            code="INTERNAL_ERROR",
            message="Ein technischer Fehler ist aufgetreten.",
            status_code=500,
        ),
    )
