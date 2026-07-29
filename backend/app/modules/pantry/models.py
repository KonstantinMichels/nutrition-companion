from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

from app.database.base import Base, utc_now

if TYPE_CHECKING:
    from app.modules.foods.models import Food, FoodMeasure


class PantryLocation(Base):
    __tablename__ = "pantry_locations"
    __table_args__ = (
        CheckConstraint("position >= 0", name="pantry_location_nonnegative_position"),
        CheckConstraint(
            "location_type IN ('pantry','refrigerator','freezer','kitchen','cellar','other')",
            name="pantry_location_valid_type",
        ),
        Index(
            "ix_pantry_location_owner_active_position",
            "owner_profile_id",
            "is_archived",
            "position",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    lots: Mapped[list[PantryStockLot]] = relationship(back_populates="location")


class PantryStockLot(Base):
    __tablename__ = "pantry_stock_lots"
    __table_args__ = (
        CheckConstraint("current_quantity >= 0", name="pantry_lot_nonnegative_quantity"),
        CheckConstraint(
            "initial_entered_quantity > 0", name="pantry_lot_positive_initial_quantity"
        ),
        CheckConstraint("normalized_unit IN ('g','ml')", name="pantry_lot_valid_unit"),
        CheckConstraint("version >= 1", name="pantry_lot_positive_version"),
        Index(
            "ix_pantry_lot_owner_active_food",
            "owner_profile_id",
            "is_archived",
            "is_depleted",
            "food_id",
        ),
        Index("ix_pantry_lot_owner_location", "owner_profile_id", "location_id"),
        Index("ix_pantry_lot_dates", "best_before_date", "use_by_date"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_id: Mapped[UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    normalized_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    initial_entered_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    initial_entered_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    initial_food_measure_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("food_measures.id", ondelete="RESTRICT")
    )
    initial_conversion_estimated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    purchase_date: Mapped[date | None] = mapped_column(Date)
    opened_date: Mapped[date | None] = mapped_column(Date)
    best_before_date: Mapped[date | None] = mapped_column(Date)
    use_by_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(1000))
    is_depleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    depleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    food: Mapped[Food] = relationship()
    location: Mapped[PantryLocation] = relationship(back_populates="lots")
    initial_food_measure: Mapped[FoodMeasure | None] = relationship(
        foreign_keys=[initial_food_measure_id]
    )
    movements: Mapped[list[PantryMovement]] = relationship(
        back_populates="stock_lot",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="PantryMovement.stock_lot_id",
        order_by="PantryMovement.created_at",
    )


class PantryMovement(Base):
    __tablename__ = "pantry_movements"
    __table_args__ = (
        CheckConstraint("normalized_unit IN ('g','ml')", name="pantry_movement_valid_unit"),
        UniqueConstraint(
            "owner_profile_id",
            "client_operation_id",
            "movement_type",
            name="uq_pantry_movement_operation_type",
        ),
        Index("ix_pantry_movement_lot_created", "stock_lot_id", "created_at"),
        Index("ix_pantry_movement_owner_operation", "owner_profile_id", "client_operation_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_lot_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_stock_lots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    normalized_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    entered_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    entered_unit_code: Mapped[str | None] = mapped_column(String(32))
    food_measure_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("food_measures.id", ondelete="RESTRICT")
    )
    conversion_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    note: Mapped[str | None] = mapped_column(String(1000))
    target_location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pantry_locations.id", ondelete="RESTRICT")
    )
    related_stock_lot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pantry_stock_lots.id", ondelete="SET NULL")
    )
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    stock_lot: Mapped[PantryStockLot] = relationship(
        back_populates="movements", foreign_keys=[stock_lot_id]
    )
