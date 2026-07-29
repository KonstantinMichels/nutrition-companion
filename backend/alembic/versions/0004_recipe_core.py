"""add Recipe Core tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("servings", sa.Numeric(12, 6), nullable=False),
        sa.Column("preparation_time_minutes", sa.Integer()),
        sa.Column("cooking_time_minutes", sa.Integer()),
        sa.Column("resting_time_minutes", sa.Integer()),
        sa.Column("finished_weight_g", sa.Numeric(18, 6)),
        sa.Column("source_type", sa.String(48), nullable=False),
        sa.Column("source_name", sa.String(160)),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("notes", sa.Text()),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("servings > 0", name="ck_recipes_positive_servings"),
        sa.CheckConstraint(
            "finished_weight_g IS NULL OR finished_weight_g > 0",
            name="ck_recipes_positive_finished_weight",
        ),
    )
    for name, cols in (
        ("ix_recipes_owner_profile_id", ["owner_profile_id"]),
        ("ix_recipes_normalized_name", ["normalized_name"]),
        ("ix_recipes_is_archived", ["is_archived"]),
        ("ix_recipe_owner_archive_updated", ["owner_profile_id", "is_archived", "updated_at"]),
    ):
        op.create_index(name, "recipes", cols)
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 9), nullable=False),
        sa.Column("unit_type", sa.String(24), nullable=False),
        sa.Column("unit_code", sa.String(32), nullable=False),
        sa.Column("food_measure_id", sa.Uuid()),
        sa.Column("normalized_quantity", sa.Numeric(30, 15), nullable=False),
        sa.Column("normalized_unit", sa.String(8), nullable=False),
        sa.Column("conversion_source", sa.String(48), nullable=False),
        sa.Column("conversion_is_estimated", sa.Boolean(), nullable=False),
        sa.Column("preparation_note", sa.String(500)),
        sa.Column("is_optional", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["food_measure_id"], ["food_measures.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("quantity > 0", name="ck_recipe_ingredients_positive_quantity"),
        sa.CheckConstraint(
            "normalized_quantity > 0", name="ck_recipe_ingredients_positive_normalized_quantity"
        ),
    )
    op.create_index("ix_recipe_ingredients_recipe_id", "recipe_ingredients", ["recipe_id"])
    op.create_index("ix_recipe_ingredients_food_id", "recipe_ingredients", ["food_id"])
    op.create_index(
        "ix_recipe_ingredient_position", "recipe_ingredients", ["recipe_id", "position"]
    )
    op.create_table(
        "recipe_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("optional_duration_minutes", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "optional_duration_minutes IS NULL OR optional_duration_minutes >= 0",
            name="ck_recipe_steps_nonnegative_duration",
        ),
    )
    op.create_index("ix_recipe_steps_recipe_id", "recipe_steps", ["recipe_id"])
    op.create_index("ix_recipe_step_position", "recipe_steps", ["recipe_id", "position"])


def downgrade() -> None:
    op.drop_table("recipe_steps")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
