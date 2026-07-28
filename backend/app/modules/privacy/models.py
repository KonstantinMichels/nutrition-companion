from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now

if TYPE_CHECKING:
    from app.modules.profiles.models import Profile


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    __table_args__ = (
        Index(
            "uq_consent_active_profile_purpose_version",
            "profile_id",
            "purpose_code",
            "consent_text_version",
            unique=True,
            postgresql_where=text("status = 'granted' AND withdrawn_at IS NULL"),
            sqlite_where=text("status = 'granted' AND withdrawn_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose_code: Mapped[str] = mapped_column(String(100), nullable=False)
    consent_text_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(48), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile: Mapped[Profile] = relationship(back_populates="consent_records")


class ProcessingPurpose(Base):
    __tablename__ = "processing_purposes"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    description_de: Mapped[str] = mapped_column(Text, nullable=False)
    data_categories: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    may_include_special_category_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    storage_location: Mapped[str] = mapped_column(String(200), nullable=False)
    retention_period: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_basis_placeholder: Mapped[str] = mapped_column(String(300), nullable=False)
    consent_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recipients_or_processors: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    deletion_behavior_de: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    registry_version: Mapped[str] = mapped_column(String(64), nullable=False)


class PrivacyAction(Base):
    __tablename__ = "privacy_actions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")


class DeletionRecord(Base):
    __tablename__ = "deletion_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    deletion_scope: Mapped[str] = mapped_column(String(48), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deleted_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmation_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
