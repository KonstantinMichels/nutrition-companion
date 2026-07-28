from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.privacy.models import ConsentRecord, ProcessingPurpose


def list_purposes(session: Session) -> list[ProcessingPurpose]:
    return list(session.scalars(select(ProcessingPurpose).order_by(ProcessingPurpose.code)))


def list_consents(session: Session, profile_id: UUID) -> list[ConsentRecord]:
    return list(
        session.scalars(
            select(ConsentRecord)
            .where(ConsentRecord.profile_id == profile_id)
            .order_by(ConsentRecord.created_at.desc())
        )
    )


def active_consent(
    session: Session,
    profile_id: UUID,
    purpose_code: str,
    consent_text_version: str,
) -> ConsentRecord | None:
    return session.scalar(
        select(ConsentRecord)
        .where(
            ConsentRecord.profile_id == profile_id,
            ConsentRecord.purpose_code == purpose_code,
            ConsentRecord.consent_text_version == consent_text_version,
            ConsentRecord.status == "granted",
            ConsentRecord.withdrawn_at.is_(None),
        )
        .order_by(ConsentRecord.granted_at.desc())
        .limit(1)
    )


def active_consents_for_version(
    session: Session,
    profile_id: UUID,
    purpose_code: str,
    consent_text_version: str,
) -> list[ConsentRecord]:
    return list(
        session.scalars(
            select(ConsentRecord).where(
                ConsentRecord.profile_id == profile_id,
                ConsentRecord.purpose_code == purpose_code,
                ConsentRecord.consent_text_version == consent_text_version,
                ConsentRecord.status == "granted",
                ConsentRecord.withdrawn_at.is_(None),
            )
        )
    )
