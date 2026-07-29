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
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import JSON_DOCUMENT, Base, utc_now

if TYPE_CHECKING:
    from app.modules.foods.models import Food, FoodMeasure
    from app.modules.profiles.models import Profile


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("servings > 0", name="positive_servings"),
        CheckConstraint(
            "finished_weight_g IS NULL OR finished_weight_g > 0", name="positive_finished_weight"
        ),
        Index("ix_recipe_owner_archive_updated", "owner_profile_id", "is_archived", "updated_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    servings: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    preparation_time_minutes: Mapped[int | None] = mapped_column(Integer)
    cooking_time_minutes: Mapped[int | None] = mapped_column(Integer)
    resting_time_minutes: Mapped[int | None] = mapped_column(Integer)
    finished_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    source_type: Mapped[str] = mapped_column(String(48), nullable=False, default="user_created")
    source_name: Mapped[str | None] = mapped_column(String(160))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False, default=list)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    owner: Mapped[Profile] = relationship(back_populates="recipes")
    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecipeIngredient.position",
    )
    steps: Mapped[list[RecipeStep]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecipeStep.position",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("normalized_quantity > 0", name="positive_normalized_quantity"),
        Index("ix_recipe_ingredient_position", "recipe_id", "position"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_id: Mapped[UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(24), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    food_measure_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("food_measures.id", ondelete="RESTRICT")
    )
    normalized_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    normalized_unit: Mapped[str] = mapped_column(String(8), nullable=False)
    conversion_source: Mapped[str] = mapped_column(String(48), nullable=False)
    conversion_is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    preparation_note: Mapped[str | None] = mapped_column(String(500))
    is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    food: Mapped[Food] = relationship()
    food_measure: Mapped[FoodMeasure | None] = relationship()


class RecipeStep(Base):
    __tablename__ = "recipe_steps"
    __table_args__ = (
        CheckConstraint(
            "optional_duration_minutes IS NULL OR optional_duration_minutes >= 0",
            name="nonnegative_duration",
        ),
        Index("ix_recipe_step_position", "recipe_id", "position"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    optional_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    recipe: Mapped[Recipe] = relationship(back_populates="steps")
