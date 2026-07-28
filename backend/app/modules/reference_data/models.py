from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now


class ReferenceSet(Base):
    __tablename__ = "reference_sets"
    __table_args__ = (UniqueConstraint("identifier", "version", name="uq_reference_set_version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    source_organization: Mapped[str] = mapped_column(String(200), nullable=False)
    edition: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    values: Mapped[list[ReferenceValue]] = relationship(
        back_populates="reference_set", cascade="all, delete-orphan", passive_deletes=True
    )


class ReferenceValue(Base):
    __tablename__ = "reference_values"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reference_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("reference_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nutrient_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name_de: Mapped[str] = mapped_column(String(120), nullable=False)
    physiological_category: Mapped[str | None] = mapped_column(String(32))
    age_min_years: Mapped[int | None]
    age_max_years_exclusive: Mapped[int | None]
    pregnancy_state: Mapped[str] = mapped_column(String(24), default="not_pregnant", nullable=False)
    breastfeeding_state: Mapped[str] = mapped_column(
        String(24), default="not_breastfeeding", nullable=False
    )
    value: Mapped[Decimal | None] = mapped_column(Numeric(14, 5))
    lower_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 5))
    upper_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 5))
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_value_category: Mapped[str] = mapped_column(String(64), nullable=False)
    source_note: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    superseded_date: Mapped[date | None] = mapped_column(Date)

    reference_set: Mapped[ReferenceSet] = relationship(back_populates="values")


class ApplicationRuleSet(Base):
    __tablename__ = "application_rule_sets"
    __table_args__ = (
        UniqueConstraint("identifier", "version", name="uq_application_rule_set_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
