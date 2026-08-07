from __future__ import annotations

from datetime import date, datetime
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now


class PantryConsumptionReconciliationBatch(Base):
    __tablename__ = "pantry_consumption_reconciliation_batches"
    __table_args__ = (
        UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_pantry_consumption_batch_operation"
        ),
        Index("ix_pantry_consumption_batch_owner_applied", "owner_profile_id", "applied_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consumption_day_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("consumption_days.id", ondelete="SET NULL"), index=True
    )
    consumption_day_date_snapshot: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    apply_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    source_day_version_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    source_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    rule_version: Mapped[str] = mapped_column(
        String(48), nullable=False, default="pantry-consumption-reconciliation/1.0"
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    requirements: Mapped[list[PantryConsumptionRequirement]] = relationship(
        back_populates="batch", cascade="all, delete-orphan", passive_deletes=True
    )
    reversals: Mapped[list[PantryConsumptionReversal]] = relationship(
        back_populates="batch", cascade="all, delete-orphan", passive_deletes=True
    )


class PantryConsumptionRequirement(Base):
    __tablename__ = "pantry_consumption_requirements"
    __table_args__ = (
        Index("ix_pantry_consumption_requirement_entry", "consumption_entry_id"),
        Index("ix_pantry_consumption_requirement_food", "food_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_consumption_reconciliation_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    consumption_day_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("consumption_days.id", ondelete="SET NULL")
    )
    consumption_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("consumption_entries.id", ondelete="SET NULL")
    )
    consumption_entry_version_snapshot: Mapped[int | None] = mapped_column(Integer)
    requirement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_context: Mapped[str] = mapped_column(String(48), nullable=False)
    food_id: Mapped[UUID | None] = mapped_column(ForeignKey("foods.id", ondelete="SET NULL"))
    food_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    recipe_ingredient_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("consumption_recipe_ingredient_snapshots.id", ondelete="SET NULL")
    )
    theoretical_required_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    previously_reconciled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(30, 15), nullable=False, default=0
    )
    selected_pantry_quantity: Mapped[Decimal] = mapped_column(
        Numeric(30, 15), nullable=False, default=0
    )
    canonical_unit: Mapped[str | None] = mapped_column(String(8))
    normalization_status: Mapped[str] = mapped_column(String(24), nullable=False)
    conversion_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    calculation_metadata: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    batch: Mapped[PantryConsumptionReconciliationBatch] = relationship(
        back_populates="requirements"
    )
    allocations: Mapped[list[PantryConsumptionAllocation]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan", passive_deletes=True
    )


class PantryConsumptionAllocation(Base):
    __tablename__ = "pantry_consumption_allocations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_consumption_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pantry_stock_lot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pantry_stock_lots.id", ondelete="SET NULL"), index=True
    )
    pantry_movement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pantry_movements.id", ondelete="SET NULL"), unique=True
    )
    food_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("foods.id", ondelete="SET NULL"), index=True
    )
    location_id_snapshot: Mapped[UUID | None] = mapped_column()
    location_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    lot_available_before: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    lot_available_after: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    lot_date_status_snapshot: Mapped[str] = mapped_column(String(24), nullable=False)
    relevant_date_snapshot: Mapped[date | None] = mapped_column(Date)
    conversion_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    requirement: Mapped[PantryConsumptionRequirement] = relationship(back_populates="allocations")
    reversal_allocations: Mapped[list[PantryConsumptionReversalAllocation]] = relationship(
        back_populates="original_allocation", cascade="all, delete-orphan", passive_deletes=True
    )


class PantryConsumptionReversal(Base):
    __tablename__ = "pantry_consumption_reversals"
    __table_args__ = (
        UniqueConstraint(
            "owner_profile_id",
            "client_operation_id",
            name="uq_pantry_consumption_reversal_operation",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reconciliation_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_consumption_reconciliation_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    batch: Mapped[PantryConsumptionReconciliationBatch] = relationship(back_populates="reversals")
    allocations: Mapped[list[PantryConsumptionReversalAllocation]] = relationship(
        back_populates="reversal", cascade="all, delete-orphan", passive_deletes=True
    )


class PantryConsumptionReversalAllocation(Base):
    __tablename__ = "pantry_consumption_reversal_allocations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reversal_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_consumption_reversals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_allocation_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_consumption_allocations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reversal_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    compensating_pantry_movement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pantry_movements.id", ondelete="SET NULL"), unique=True
    )
    lot_quantity_before: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    lot_quantity_after: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    reversal: Mapped[PantryConsumptionReversal] = relationship(back_populates="allocations")
    original_allocation: Mapped[PantryConsumptionAllocation] = relationship(
        back_populates="reversal_allocations"
    )
