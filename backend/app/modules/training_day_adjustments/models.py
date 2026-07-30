from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now


class TrainingSession(Base):
    __tablename__ = "training_sessions"
    __table_args__ = (Index("ix_training_session_owner_date", "owner_profile_id", "session_date"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_start_time: Mapped[time | None] = mapped_column(Time)
    sport_type: Mapped[str] = mapped_column(String(32), nullable=False)
    session_type: Mapped[str] = mapped_column(String(32), nullable=False)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    perceived_intensity: Mapped[str] = mapped_column(String(16), nullable=False)
    baseline_inclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="planned", index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrainingAdjustmentPreference(Base):
    __tablename__ = "training_adjustment_preferences"
    __table_args__ = (
        Index(
            "uq_training_preference_default",
            "owner_profile_id",
            unique=True,
            postgresql_where=text("is_default = true AND is_archived = false"),
            sqlite_where=text("is_default = 1 AND is_archived = 0"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_baseline_assessment_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="latest_usable"
    )
    explicit_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL")
    )
    default_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    positive_energy_cap_kcal: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=300
    )
    negative_energy_cap_kcal: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=250
    )
    relative_energy_cap: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0.15")
    )
    carbohydrate_adjustments_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    redistribution_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    minimum_rest_day_target_kcal: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    include_cancelled_sessions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class TrainingAdjustmentBatch(Base):
    __tablename__ = "training_adjustment_batches"
    __table_args__ = (
        Index(
            "uq_training_adjustment_operation",
            "owner_profile_id",
            "client_operation_id",
            unique=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    source_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    preference_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("training_adjustment_preferences.id", ondelete="SET NULL")
    )
    iso_week_start: Mapped[date | None] = mapped_column(Date)
    single_date: Mapped[date | None] = mapped_column(Date)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    preview_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adjustments: Mapped[list[TrainingDayTargetAdjustment]] = relationship(
        back_populates="batch", cascade="all, delete-orphan", passive_deletes=True
    )


class TrainingDayTargetAdjustment(Base):
    __tablename__ = "training_day_target_adjustments"
    __table_args__ = (
        Index("ix_training_adjustment_owner_date", "owner_profile_id", "adjustment_date"),
        Index(
            "uq_training_adjustment_active_date",
            "owner_profile_id",
            "adjustment_date",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("training_adjustment_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    load_category: Mapped[str] = mapped_column(String(24), nullable=False)
    baseline_energy_target_kcal: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    energy_delta_kcal: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    adjusted_energy_target_kcal: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    carbohydrate_delta_g: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    baseline_carbohydrate_target_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    adjusted_carbohydrate_target_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    protein_target_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    safety_validation_status: Mapped[str] = mapped_column(String(24), nullable=False)
    calculation_metadata: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    batch: Mapped[TrainingAdjustmentBatch] = relationship(back_populates="adjustments")
