"""add manual daily meal planning

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_meal_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_daily_meal_plans_owner_profile_id", "daily_meal_plans", ["owner_profile_id"]
    )
    op.create_index("ix_daily_meal_plans_assessment_id", "daily_meal_plans", ["assessment_id"])
    op.create_index(
        "ix_daily_plan_owner_date", "daily_meal_plans", ["owner_profile_id", "plan_date"]
    )
    op.create_index(
        "uq_daily_plan_active_owner_date",
        "daily_meal_plans",
        ["owner_profile_id", "plan_date"],
        unique=True,
        postgresql_where=sa.text("is_archived = false"),
    )
    op.create_table(
        "meals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("daily_plan_id", sa.Uuid(), nullable=False),
        sa.Column("meal_type", sa.String(length=32), nullable=False),
        sa.Column("custom_name", sa.String(length=200), nullable=True),
        sa.Column("planned_time", sa.Time(timezone=False), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="meal_nonnegative_position"),
        sa.ForeignKeyConstraint(["daily_plan_id"], ["daily_meal_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meals_daily_plan_id", "meals", ["daily_plan_id"])
    op.create_index("ix_meal_plan_position", "meals", ["daily_plan_id", "position"])
    op.create_table(
        "meal_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("meal_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.String(length=16), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("food_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_portion_count", sa.Numeric(18, 9), nullable=True),
        sa.Column("food_quantity", sa.Numeric(18, 9), nullable=True),
        sa.Column("food_unit_code", sa.String(length=32), nullable=True),
        sa.Column("food_measure_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="entry_nonnegative_position"),
        sa.CheckConstraint(
            "recipe_portion_count IS NULL OR recipe_portion_count > 0",
            name="entry_positive_recipe_portions",
        ),
        sa.CheckConstraint(
            "food_quantity IS NULL OR food_quantity > 0", name="entry_positive_food_quantity"
        ),
        sa.CheckConstraint("entry_type IN ('recipe', 'food')", name="entry_valid_type"),
        sa.CheckConstraint(
            "(entry_type = 'recipe' AND recipe_id IS NOT NULL "
            "AND recipe_portion_count IS NOT NULL AND food_id IS NULL "
            "AND food_quantity IS NULL AND food_unit_code IS NULL "
            "AND food_measure_id IS NULL) OR (entry_type = 'food' "
            "AND food_id IS NOT NULL AND food_quantity IS NOT NULL "
            "AND recipe_id IS NULL AND recipe_portion_count IS NULL "
            "AND (food_unit_code IS NOT NULL OR food_measure_id IS NOT NULL))",
            name="entry_source_shape",
        ),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["food_measure_id"], ["food_measures.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meal_entries_meal_id", "meal_entries", ["meal_id"])
    op.create_index("ix_meal_entries_recipe_id", "meal_entries", ["recipe_id"])
    op.create_index("ix_meal_entries_food_id", "meal_entries", ["food_id"])
    op.create_index("ix_meal_entry_position", "meal_entries", ["meal_id", "position"])


def downgrade() -> None:
    op.drop_table("meal_entries")
    op.drop_table("meals")
    op.drop_table("daily_meal_plans")
