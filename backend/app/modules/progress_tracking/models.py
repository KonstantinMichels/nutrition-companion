from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, utc_now


class BodyWeightObservation(Base):
    __tablename__ = "body_weight_observations"
    __table_args__ = (Index("ix_progress_weight_profile_date", "owner_profile_id", "observed_on"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    observed_time: Mapped[time | None] = mapped_column(Time)
    normalized_weight_kg: Mapped[Decimal] = mapped_column(Numeric(15, 8), nullable=False)
    entered_weight: Mapped[Decimal] = mapped_column(Numeric(15, 8), nullable=False)
    entered_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    source_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"), unique=True
    )
    measurement_context: Mapped[str] = mapped_column(
        String(24), nullable=False, default="unspecified"
    )
    note: Mapped[str | None] = mapped_column(Text)
    unusual_change_confirmed: Mapped[bool] = mapped_column(nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class BodyMeasurementObservation(Base):
    __tablename__ = "body_measurement_observations"
    __table_args__ = (
        Index("ix_progress_measurement_profile_date", "owner_profile_id", "observed_on"),
        Index("ix_progress_measurement_profile_type", "owner_profile_id", "measurement_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    measurement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    observed_time: Mapped[time | None] = mapped_column(Time)
    normalized_value_cm: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    entered_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    entered_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    measurement_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unspecified"
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class BodyCompositionObservation(Base):
    __tablename__ = "body_composition_observations"
    __table_args__ = (
        Index("ix_progress_composition_profile_date", "owner_profile_id", "observed_on"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    observed_time: Mapped[time | None] = mapped_column(Time)
    body_fat_percent: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    lean_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    fat_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    measurement_method: Mapped[str] = mapped_column(String(40), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ProgressGoal(Base):
    __tablename__ = "progress_goals"
    __table_args__ = (
        Index(
            "ix_progress_goal_one_active",
            "owner_profile_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_type: Mapped[str] = mapped_column(String(24), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    start_observation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("body_weight_observations.id", ondelete="SET NULL")
    )
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    target_weight_min_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    target_weight_max_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    target_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
