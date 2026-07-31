from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

import app.database.models as _database_models  # noqa: F401  # register ORM metadata
from app.core.branding import API_TITLE, PRODUCT_NAME
from app.core.config import get_settings
from app.core.errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging, request_log_middleware
from app.core.security import assert_safe_runtime_configuration
from app.modules.consumption_tracking.router import router as consumption_router
from app.modules.daily_meal_planning.router import router as daily_plans_router
from app.modules.energy_calibration.router import router as energy_calibration_router
from app.modules.foods.router import router as foods_router
from app.modules.meal_plan_automation.router import router as automation_router
from app.modules.nutrition_assessment.router import router as assessment_router
from app.modules.pantry.router import router as pantry_router
from app.modules.pantry_aware_shopping.router import router as pantry_aware_shopping_router
from app.modules.pantry_recipe_availability.router import (
    router as pantry_recipe_availability_router,
)
from app.modules.privacy.router import router as privacy_router
from app.modules.profiles.router import router as profiles_router
from app.modules.progress_tracking.router import router as progress_router
from app.modules.purchase_to_pantry.router import router as purchase_to_pantry_router
from app.modules.recipe_target_comparison.router import router as comparison_router
from app.modules.recipes.router import router as recipes_router
from app.modules.reference_data.router import router as reference_data_router
from app.modules.shopping_lists.router import router as shopping_lists_router
from app.modules.training_day_adjustments.router import adjustments as training_adjustments_router
from app.modules.training_day_adjustments.router import preferences as training_preferences_router
from app.modules.training_day_adjustments.router import sessions as training_sessions_router
from app.modules.weekly_meal_planning.router import router as weekly_plans_router

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    assert_safe_runtime_configuration(settings)
    yield


app = FastAPI(
    title=API_TITLE,
    version="0.1.0",
    description=(
        f"{PRODUCT_NAME} provides transparent nutrition estimates for the supported MVP scope. "
        "It is not intended for diagnosis or treatment."
    ),
    lifespan=lifespan,
)

app.middleware("http")(request_log_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID"],
)

app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unexpected_error_handler)

app.include_router(profiles_router)
app.include_router(consumption_router)
app.include_router(progress_router)
app.include_router(training_sessions_router)
app.include_router(training_preferences_router)
app.include_router(training_adjustments_router)
app.include_router(energy_calibration_router)
app.include_router(privacy_router)
app.include_router(reference_data_router)
app.include_router(daily_plans_router)
app.include_router(pantry_router)
app.include_router(automation_router)
app.include_router(pantry_aware_shopping_router)
app.include_router(shopping_lists_router)
app.include_router(purchase_to_pantry_router)
app.include_router(weekly_plans_router)
app.include_router(comparison_router)
app.include_router(assessment_router)
app.include_router(pantry_recipe_availability_router)
app.include_router(foods_router)
app.include_router(recipes_router)


@app.get("/health", tags=["operations"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "nutrition-companion-api",
        "environment": settings.app_env,
    }
