from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utc_now

if TYPE_CHECKING:
    from app.modules.profiles.models import Profile


class Food(Base):
    __tablename__ = "foods"
    __table_args__ = (
        CheckConstraint("reference_quantity = 100", name="reference_quantity_100"),
        CheckConstraint("reference_unit IN ('g', 'ml')", name="reference_unit"),
        CheckConstraint(
            "density_g_per_ml IS NULL OR density_g_per_ml > 0", name="positive_density"
        ),
        Index("ix_food_owner_archive_name", "owner_profile_id", "is_archived", "normalized_name"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(160))
    normalized_brand: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    category_code: Mapped[str | None] = mapped_column(String(48), index=True)
    food_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user_created")
    source_type: Mapped[str] = mapped_column(String(48), nullable=False, default="user_entered")
    source_name: Mapped[str | None] = mapped_column(String(160))
    source_external_id: Mapped[str | None] = mapped_column(String(200))
    source_version: Mapped[str | None] = mapped_column(String(100))
    reference_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal(100)
    )
    reference_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    density_g_per_ml: Mapped[Decimal | None] = mapped_column(Numeric(18, 9))
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    owner: Mapped[Profile | None] = relationship(back_populates="foods")
    nutrients: Mapped[list[FoodNutrient]] = relationship(
        back_populates="food", cascade="all, delete-orphan", passive_deletes=True
    )
    measures: Mapped[list[FoodMeasure]] = relationship(
        back_populates="food", cascade="all, delete-orphan", passive_deletes=True
    )


class FoodNutrient(Base):
    __tablename__ = "food_nutrients"
    __table_args__ = (
        UniqueConstraint("food_id", "nutrient_code", name="uq_food_nutrient_code"),
        CheckConstraint("amount >= 0", name="nonnegative_amount"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    food_id: Mapped[UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nutrient_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    value_source: Mapped[str] = mapped_column(String(48), nullable=False)
    source_note: Mapped[str | None] = mapped_column(String(500))
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    food: Mapped[Food] = relationship(back_populates="nutrients")


class FoodMeasure(Base):
    __tablename__ = "food_measures"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("equivalent_quantity > 0", name="positive_equivalent"),
        CheckConstraint("equivalent_unit IN ('g', 'ml')", name="equivalent_unit"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    food_id: Mapped[UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    equivalent_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    equivalent_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_type: Mapped[str] = mapped_column(String(48), nullable=False, default="user_entered")
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    food: Mapped[Food] = relationship(back_populates="measures")
