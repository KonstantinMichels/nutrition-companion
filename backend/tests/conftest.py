from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any

import fastapi.routing
import httpx2
import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["ALLOW_INSECURE_LOCAL_HTTP"] = "true"
os.environ["USE_DEVELOPMENT_PROFILE_RESOLVER"] = "true"

import app.database.models
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.privacy.models import ProcessingPurpose
from app.modules.privacy.registry import (
    PROCESSING_PURPOSE_REGISTRY_VERSION,
    PROCESSING_PURPOSES,
)
from app.modules.reference_data.seed import seed_all


@pytest.fixture(autouse=True)
def execute_sync_routes_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep ASGI tests deterministic where this sandbox cannot wake worker threads.

    Production FastAPI still dispatches the synchronous SQLAlchemy routes through
    its normal AnyIO thread pool. Only the in-process test adapter is replaced.
    """

    async def run_inline(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi.routing, "run_in_threadpool", run_inline)


class ApiClient:
    """Small synchronous facade over HTTPX2's in-process ASGI transport."""

    def request(self, method: str, url: str, **kwargs: Any) -> httpx2.Response:
        async def send() -> httpx2.Response:
            transport = httpx2.ASGITransport(app=app, raise_app_exceptions=False)
            async with httpx2.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                follow_redirects=True,
            ) as async_client:
                return await async_client.request(method, url, **kwargs)

        return asyncio.run(send())

    def get(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("DELETE", url, **kwargs)


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[ApiClient, None, None]:
    async def override_get_db() -> AsyncGenerator[Session, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield ApiClient()
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_purposes(db_session: Session) -> None:
    for item in PROCESSING_PURPOSES:
        db_session.add(
            ProcessingPurpose(
                **item,
                registry_version=PROCESSING_PURPOSE_REGISTRY_VERSION,
            )
        )
    db_session.commit()


@pytest.fixture
def seeded_database(db_session: Session) -> None:
    counts = seed_all(db_session)
    assert counts["processing_purposes"] == 17


@pytest.fixture
def complete_profile_payload() -> dict[str, object]:
    return {
        "birth_date": "1990-06-15",
        "physiological_category": "reference_category_a",
        "height_cm": "180,0",
        "current_weight_kg": "82,5",
        "dietary_preference": "mixed",
        "preferred_meals_per_day": 3,
        "preferred_meal_timing": "morgens, mittags und abends",
        "measurements": [
            {
                "measurement_type": "body_fat_percentage",
                "value": "20,0",
                "unit": "%",
                "measured_at": "2026-07-20",
                "source_type": "device_estimate",
            },
            {
                "measurement_type": "waist_circumference",
                "value": "88,5",
                "unit": "cm",
                "measured_at": "2026-07-20",
                "source_type": "measured",
            },
            {
                "measurement_type": "hip_circumference",
                "value": "101,0",
                "unit": "cm",
                "measured_at": "2026-07-20",
                "source_type": "measured",
            },
        ],
    }


@pytest.fixture
def saved_profile(client: ApiClient, complete_profile_payload: dict[str, object]) -> None:
    assert client.put("/api/v1/profile", json=complete_profile_payload).status_code == 200
    assert (
        client.put(
            "/api/v1/profile/activity",
            json={
                "occupational_activity_category": "seated_with_walking",
                "average_daily_steps": 7000,
                "active_commuting": True,
                "movement_notes": "Normale Alltagsbewegung",
                "sports": [
                    {
                        "sport_type": "strength_training",
                        "sessions_per_week": "3",
                        "minutes_per_session": 60,
                        "intensity": "moderate",
                    }
                ],
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/profile/goal",
            json={"goal_type": "lose_weight", "desired_intensity": "mild"},
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/profile/restrictions",
            json={
                "restrictions": [
                    {
                        "restriction_type": "allergy",
                        "value": "Erdnuss",
                        "hard_exclusion": True,
                    }
                ]
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/profile/health-screening",
            json={
                "pregnant": False,
                "breastfeeding": False,
                "diagnosed_eating_disorder": False,
                "diabetes": False,
                "kidney_disease": False,
                "liver_disease": False,
                "medically_prescribed_diet": False,
                "serious_metabolic_condition": False,
                "other_professional_nutrition_condition": False,
            },
        ).status_code
        == 200
    )
