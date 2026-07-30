from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
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
