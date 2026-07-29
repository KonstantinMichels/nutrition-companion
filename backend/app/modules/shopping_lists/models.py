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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now

if TYPE_CHECKING:
    from app.modules.daily_meal_planning.models import DailyMealPlan
    from app.modules.foods.models import Food, FoodMeasure


class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('manual','daily_plan','weekly_plan','mixed')",
            name="shopping_list_valid_source",
        ),
        CheckConstraint("status IN ('open','completed')", name="shopping_list_valid_status"),
        CheckConstraint("version >= 1", name="shopping_list_positive_version"),
        Index(
            "ix_shopping_list_owner_active_updated", "owner_profile_id", "is_archived", "updated_at"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, default="manual")
    source_daily_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("daily_meal_plans.id", ondelete="SET NULL"), index=True
    )
    source_week_start: Mapped[date | None] = mapped_column(Date)
    source_week_end: Mapped[date | None] = mapped_column(Date)
    pantry_considered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    source_summary: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    warning_codes: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    source_daily_plan: Mapped[DailyMealPlan | None] = relationship()
    items: Mapped[list[ShoppingListItem]] = relationship(
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ShoppingListItem.position",
    )


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"
    __table_args__ = (
        CheckConstraint("item_type IN ('food','manual')", name="shopping_item_valid_type"),
        CheckConstraint("origin_type IN ('generated','manual')", name="shopping_item_valid_origin"),
        CheckConstraint(
            "source_status IN ('current','changed','no_longer_required','source_unavailable')",
            name="shopping_item_valid_source_status",
        ),
        CheckConstraint("position >= 0", name="shopping_item_nonnegative_position"),
        CheckConstraint(
            "canonical_unit IS NULL OR canonical_unit IN ('g','ml')",
            name="shopping_item_valid_unit",
        ),
        CheckConstraint(
            "(item_type='food' AND food_id IS NOT NULL AND manual_name IS NULL) OR "
            "(item_type='manual' AND food_id IS NULL AND manual_name IS NOT NULL)",
            name="shopping_item_source_shape",
        ),
        Index(
            "ix_shopping_item_list_category_position",
            "shopping_list_id",
            "category_code",
            "position",
        ),
        Index("ix_shopping_item_list_checked", "shopping_list_id", "is_checked"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    shopping_list_id: Mapped[UUID] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(String(16), nullable=False)
    origin_type: Mapped[str] = mapped_column(String(16), nullable=False)
    food_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), index=True
    )
    food_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    manual_name: Mapped[str | None] = mapped_column(String(200))
    category_code: Mapped[str] = mapped_column(String(48), nullable=False, default="other")
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_unit: Mapped[str | None] = mapped_column(String(8))
    required_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    pantry_available_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    suggested_purchase_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    purchase_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    purchase_unit_code: Mapped[str | None] = mapped_column(String(32))
    purchase_food_measure_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("food_measures.id", ondelete="RESTRICT")
    )
    manual_quantity: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    manual_unit_label: Mapped[str | None] = mapped_column(String(32))
    quantity_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_status: Mapped[str] = mapped_column(String(32), nullable=False, default="current")
    warning_codes: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False, default=list)
    note: Mapped[str | None] = mapped_column(String(1000))
    pantry_handoff_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default="not_started"
    )
    pantry_transferred_quantity: Mapped[Decimal] = mapped_column(
        Numeric(30, 15), nullable=False, default=Decimal(0)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")
    food: Mapped[Food | None] = relationship()
    purchase_food_measure: Mapped[FoodMeasure | None] = relationship()
    sources: Mapped[list[ShoppingListItemSource]] = relationship(
        back_populates="item", cascade="all, delete-orphan", passive_deletes=True
    )


class ShoppingListItemSource(Base):
    __tablename__ = "shopping_list_item_sources"
    __table_args__ = (
        Index("ix_shopping_source_item", "shopping_list_item_id"),
        Index("ix_shopping_source_plan_date", "daily_plan_id", "plan_date"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    shopping_list_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("shopping_list_items.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    daily_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("daily_meal_plans.id", ondelete="SET NULL")
    )
    plan_date: Mapped[date | None] = mapped_column(Date)
    meal_id: Mapped[UUID | None] = mapped_column(ForeignKey("meals.id", ondelete="SET NULL"))
    meal_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    meal_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meal_entries.id", ondelete="SET NULL")
    )
    recipe_id: Mapped[UUID | None] = mapped_column(ForeignKey("recipes.id", ondelete="SET NULL"))
    recipe_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    recipe_ingredient_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipe_ingredients.id", ondelete="SET NULL")
    )
    food_id: Mapped[UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    unit: Mapped[str] = mapped_column(String(8), nullable=False)
    conversion_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    warning_codes: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    item: Mapped[ShoppingListItem] = relationship(back_populates="sources")
