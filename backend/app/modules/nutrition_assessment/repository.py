from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.nutrition_assessment.models import Assessment

_DETAIL_OPTIONS = (
    selectinload(Assessment.metrics),
    selectinload(Assessment.safety_flags),
)


def get_assessment(session: Session, profile_id: UUID, assessment_id: UUID) -> Assessment | None:
    return session.scalar(
        select(Assessment)
        .where(Assessment.id == assessment_id, Assessment.profile_id == profile_id)
        .options(*_DETAIL_OPTIONS)
    )


def get_by_client_request(
    session: Session, profile_id: UUID, client_request_id: UUID
) -> Assessment | None:
    return session.scalar(
        select(Assessment)
        .where(
            Assessment.profile_id == profile_id,
            Assessment.client_request_id == client_request_id,
        )
        .options(*_DETAIL_OPTIONS)
    )


def latest_assessment(session: Session, profile_id: UUID) -> Assessment | None:
    return session.scalar(
        select(Assessment)
        .where(Assessment.profile_id == profile_id)
        .options(*_DETAIL_OPTIONS)
        .order_by(Assessment.calculated_at.desc(), Assessment.id.desc())
        .limit(1)
    )


def list_assessments(
    session: Session, profile_id: UUID, *, limit: int, offset: int
) -> tuple[list[Assessment], int]:
    items = list(
        session.scalars(
            select(Assessment)
            .where(Assessment.profile_id == profile_id)
            .options(selectinload(Assessment.safety_flags))
            .order_by(Assessment.calculated_at.desc(), Assessment.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    total = session.scalar(
        select(func.count()).select_from(Assessment).where(Assessment.profile_id == profile_id)
    )
    return items, int(total or 0)


def list_assessments_with_metrics(session: Session, profile_id: UUID) -> list[Assessment]:
    return list(
        session.scalars(
            select(Assessment)
            .where(Assessment.profile_id == profile_id)
            .options(*_DETAIL_OPTIONS)
            .order_by(Assessment.calculated_at.desc(), Assessment.id.desc())
        )
    )
