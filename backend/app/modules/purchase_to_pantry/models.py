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
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utc_now

if TYPE_CHECKING:
    from app.modules.pantry.models import PantryLocation, PantryMovement
    from app.modules.shopping_lists.models import ShoppingList, ShoppingListItem


class PurchaseToPantryHandoff(Base):
    __tablename__ = "purchase_to_pantry_handoffs"
    __table_args__ = (
        UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_purchase_handoff_operation"
        ),
        Index("ix_purchase_handoff_list_created", "shopping_list_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shopping_list_id: Mapped[UUID] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shopping_list_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    client_operation_id: Mapped[UUID] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    shopping_list: Mapped[ShoppingList] = relationship()
    items: Mapped[list[PurchaseToPantryHandoffItem]] = relationship(
        back_populates="handoff", cascade="all, delete-orphan", passive_deletes=True
    )


class PurchaseToPantryHandoffItem(Base):
    __tablename__ = "purchase_to_pantry_handoff_items"
    __table_args__ = (
        CheckConstraint(
            "actual_transferred_quantity > 0", name="purchase_handoff_item_positive_quantity"
        ),
        Index("ix_purchase_handoff_item_shopping_item", "shopping_list_item_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    handoff_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_to_pantry_handoffs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shopping_list_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("shopping_list_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    food_id: Mapped[UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False
    )
    shopping_item_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    planned_purchase_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    planned_purchase_unit: Mapped[str | None] = mapped_column(String(32))
    actual_transferred_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    mark_item_handoff_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    handoff: Mapped[PurchaseToPantryHandoff] = relationship(back_populates="items")
    shopping_list_item: Mapped[ShoppingListItem] = relationship()
    destinations: Mapped[list[PurchaseToPantryDestination]] = relationship(
        back_populates="handoff_item", cascade="all, delete-orphan", passive_deletes=True
    )


class PurchaseToPantryDestination(Base):
    __tablename__ = "purchase_to_pantry_destinations"
    __table_args__ = (
        CheckConstraint(
            "destination_type IN ('new_stock_lot','existing_stock_lot')",
            name="purchase_destination_valid_type",
        ),
        CheckConstraint("normalized_quantity > 0", name="purchase_destination_positive_quantity"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    handoff_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_to_pantry_handoff_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_type: Mapped[str] = mapped_column(String(24), nullable=False)
    pantry_location_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_locations.id", ondelete="RESTRICT"), nullable=False
    )
    target_stock_lot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pantry_stock_lots.id", ondelete="RESTRICT")
    )
    created_stock_lot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pantry_stock_lots.id", ondelete="RESTRICT")
    )
    pantry_movement_id: Mapped[UUID] = mapped_column(
        ForeignKey("pantry_movements.id", ondelete="RESTRICT"), nullable=False
    )
    entered_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    entered_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    food_measure_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("food_measures.id", ondelete="RESTRICT")
    )
    normalized_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    normalized_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    conversion_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    opened_date: Mapped[date | None] = mapped_column(Date)
    best_before_date: Mapped[date | None] = mapped_column(Date)
    use_by_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    handoff_item: Mapped[PurchaseToPantryHandoffItem] = relationship(back_populates="destinations")
    location: Mapped[PantryLocation] = relationship()
    movement: Mapped[PantryMovement] = relationship()
