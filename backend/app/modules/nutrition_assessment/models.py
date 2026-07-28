from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now

if TYPE_CHECKING:
    from app.modules.profiles.models import Profile


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("profile_id", "client_request_id", name="uq_assessment_client_request"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_request_id: Mapped[UUID] = mapped_column(nullable=False)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    supported_scope_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("reference_sets.id", ondelete="RESTRICT"), nullable=False
    )
    application_rule_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("application_rule_sets.id", ondelete="RESTRICT"), nullable=False
    )
    reference_set_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    reference_set_version: Mapped[str] = mapped_column(String(100), nullable=False)
    application_rule_set_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    application_rule_set_version: Mapped[str] = mapped_column(String(100), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    summary: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="assessments")
    metrics: Mapped[list[AssessmentMetric]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AssessmentMetric.metric_code",
    )
    safety_flags: Mapped[list[SafetyFlag]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SafetyFlag.code",
    )


class AssessmentMetric(Base):
    __tablename__ = "assessment_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    display_value: Mapped[str] = mapped_column(String(200), nullable=False)
    lower_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    upper_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    method_code: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation_de: Mapped[str] = mapped_column(Text, nullable=False)
    limitations_de: Mapped[str] = mapped_column(Text, nullable=False)
    calculation_inputs: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    source_metadata: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    application_rule_identifier: Mapped[str | None] = mapped_column(String(100))
    confidence_type: Mapped[str] = mapped_column(String(32), nullable=False)

    assessment: Mapped[Assessment] = relationship(back_populates="metrics")


class SafetyFlag(Base):
    __tablename__ = "safety_flags"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    explanation_de: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action_de: Mapped[str] = mapped_column(Text, nullable=False)

    assessment: Mapped[Assessment] = relationship(back_populates="safety_flags")
