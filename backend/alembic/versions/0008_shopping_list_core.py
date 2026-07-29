"""add shopping list core

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("source_daily_plan_id", sa.Uuid()),
        sa.Column("source_week_start", sa.Date()),
        sa.Column("source_week_end", sa.Date()),
        sa.Column("pantry_considered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("refreshed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("source_summary", sa.JSON(), nullable=False),
        sa.Column("warning_codes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('manual','daily_plan','weekly_plan','mixed')",
            name="shopping_list_valid_source",
        ),
        sa.CheckConstraint("status IN ('open','completed')", name="shopping_list_valid_status"),
        sa.CheckConstraint("version >= 1", name="shopping_list_positive_version"),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_daily_plan_id"], ["daily_meal_plans.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopping_lists_owner_profile_id", "shopping_lists", ["owner_profile_id"])
    op.create_index(
        "ix_shopping_lists_source_daily_plan_id", "shopping_lists", ["source_daily_plan_id"]
    )
    op.create_index(
        "ix_shopping_list_owner_active_updated",
        "shopping_lists",
        ["owner_profile_id", "is_archived", "updated_at"],
    )
    op.create_table(
        "shopping_list_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shopping_list_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(16), nullable=False),
        sa.Column("origin_type", sa.String(16), nullable=False),
        sa.Column("food_id", sa.Uuid()),
        sa.Column("food_name_snapshot", sa.String(200)),
        sa.Column("manual_name", sa.String(200)),
        sa.Column("category_code", sa.String(48), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("canonical_unit", sa.String(8)),
        sa.Column("required_quantity", sa.Numeric(30, 15)),
        sa.Column("pantry_available_quantity", sa.Numeric(30, 15)),
        sa.Column("suggested_purchase_quantity", sa.Numeric(30, 15)),
        sa.Column("purchase_quantity", sa.Numeric(30, 15)),
        sa.Column("purchase_unit_code", sa.String(32)),
        sa.Column("purchase_food_measure_id", sa.Uuid()),
        sa.Column("manual_quantity", sa.Numeric(30, 15)),
        sa.Column("manual_unit_label", sa.String(32)),
        sa.Column("quantity_overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("source_status", sa.String(32), nullable=False, server_default="current"),
        sa.Column("warning_codes", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("item_type IN ('food','manual')", name="shopping_item_valid_type"),
        sa.CheckConstraint(
            "origin_type IN ('generated','manual')", name="shopping_item_valid_origin"
        ),
        sa.CheckConstraint(
            "source_status IN ('current','changed','no_longer_required','source_unavailable')",
            name="shopping_item_valid_source_status",
        ),
        sa.CheckConstraint("position >= 0", name="shopping_item_nonnegative_position"),
        sa.CheckConstraint(
            "canonical_unit IS NULL OR canonical_unit IN ('g','ml')",
            name="shopping_item_valid_unit",
        ),
        sa.CheckConstraint(
            "(item_type='food' AND food_id IS NOT NULL AND manual_name IS NULL) OR "
            "(item_type='manual' AND food_id IS NULL AND manual_name IS NOT NULL)",
            name="shopping_item_source_shape",
        ),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["purchase_food_measure_id"], ["food_measures.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, cols in (
        ("ix_shopping_list_items_shopping_list_id", ["shopping_list_id"]),
        ("ix_shopping_list_items_food_id", ["food_id"]),
        (
            "ix_shopping_item_list_category_position",
            ["shopping_list_id", "category_code", "position"],
        ),
        ("ix_shopping_item_list_checked", ["shopping_list_id", "is_checked"]),
    ):
        op.create_index(name, "shopping_list_items", cols)
    op.create_table(
        "shopping_list_item_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shopping_list_item_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("daily_plan_id", sa.Uuid()),
        sa.Column("plan_date", sa.Date()),
        sa.Column("meal_id", sa.Uuid()),
        sa.Column("meal_name_snapshot", sa.String(200)),
        sa.Column("meal_entry_id", sa.Uuid()),
        sa.Column("recipe_id", sa.Uuid()),
        sa.Column("recipe_name_snapshot", sa.String(200)),
        sa.Column("recipe_ingredient_id", sa.Uuid()),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(30, 15), nullable=False),
        sa.Column("unit", sa.String(8), nullable=False),
        sa.Column("conversion_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("warning_codes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["shopping_list_item_id"], ["shopping_list_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["daily_plan_id"], ["daily_meal_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["meal_entry_id"], ["meal_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["recipe_ingredient_id"], ["recipe_ingredients.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shopping_source_item", "shopping_list_item_sources", ["shopping_list_item_id"]
    )
    op.create_index(
        "ix_shopping_source_plan_date", "shopping_list_item_sources", ["daily_plan_id", "plan_date"]
    )


def downgrade() -> None:
    op.drop_table("shopping_list_item_sources")
    op.drop_table("shopping_list_items")
    op.drop_table("shopping_lists")
