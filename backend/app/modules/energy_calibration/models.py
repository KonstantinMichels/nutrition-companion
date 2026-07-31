from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import JSON_DOCUMENT, Base, utc_now


class EnergyCalibrationRecord(Base):
    __tablename__ = "energy_calibration_records"
    __table_args__ = (
        UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_energy_calibration_operation"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    source_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    created_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False, default="target_response_proxy")
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    adherence: Mapped[str] = mapped_column(String(16), nullable=False)
    context_stability: Mapped[str] = mapped_column(String(24), nullable=False)
    proposed_adjustment_kcal_per_day: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    accepted_adjustment_kcal_per_day: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    evidence_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    proposal_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    rules_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class EnergyCalibrationConsumptionEvidence(Base):
    __tablename__ = "energy_calibration_consumption_days"
    __table_args__ = (
        UniqueConstraint(
            "calibration_record_id", "source_id", name="uq_calibration_consumption_evidence"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    calibration_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("energy_calibration_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("consumption_days.id", ondelete="SET NULL"), index=True
    )
    source_version_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(String(64))
    evidence_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_value_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    evidence_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class EnergyCalibrationWeightEvidence(Base):
    __tablename__ = "energy_calibration_weight_observations"
    __table_args__ = (
        UniqueConstraint(
            "calibration_record_id", "source_id", name="uq_calibration_weight_evidence"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    calibration_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("energy_calibration_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("body_weight_observations.id", ondelete="SET NULL"), index=True
    )
    included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(String(64))
    evidence_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_value_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    evidence_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
