"""add Food Core tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "foods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid()),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column("brand", sa.String(160)),
        sa.Column("normalized_brand", sa.String(160)),
        sa.Column("description", sa.Text()),
        sa.Column("category_code", sa.String(48)),
        sa.Column("food_type", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(48), nullable=False),
        sa.Column("source_name", sa.String(160)),
        sa.Column("source_external_id", sa.String(200)),
        sa.Column("source_version", sa.String(100)),
        sa.Column("reference_quantity", sa.Numeric(12, 6), nullable=False),
        sa.Column("reference_unit", sa.String(8), nullable=False),
        sa.Column("density_g_per_ml", sa.Numeric(18, 9)),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("reference_quantity = 100", name="ck_foods_reference_quantity_100"),
        sa.CheckConstraint("reference_unit IN ('g', 'ml')", name="ck_foods_reference_unit"),
        sa.CheckConstraint(
            "density_g_per_ml IS NULL OR density_g_per_ml > 0", name="ck_foods_positive_density"
        ),
    )
    for name, cols in (
        ("ix_foods_owner_profile_id", ["owner_profile_id"]),
        ("ix_foods_normalized_name", ["normalized_name"]),
        ("ix_foods_category_code", ["category_code"]),
        ("ix_foods_is_archived", ["is_archived"]),
        ("ix_food_owner_archive_name", ["owner_profile_id", "is_archived", "normalized_name"]),
    ):
        op.create_index(name, "foods", cols)
    op.create_table(
        "food_nutrients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_code", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(30, 15), nullable=False),
        sa.Column("unit", sa.String(24), nullable=False),
        sa.Column("value_source", sa.String(48), nullable=False),
        sa.Column("source_note", sa.String(500)),
        sa.Column("is_estimated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("food_id", "nutrient_code", name="uq_food_nutrient_code"),
        sa.CheckConstraint("amount >= 0", name="ck_food_nutrients_nonnegative_amount"),
    )
    op.create_index("ix_food_nutrients_food_id", "food_nutrients", ["food_id"])
    op.create_index("ix_food_nutrients_nutrient_code", "food_nutrients", ["nutrient_code"])
    op.create_table(
        "food_measures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 9), nullable=False),
        sa.Column("unit_code", sa.String(32), nullable=False),
        sa.Column("equivalent_quantity", sa.Numeric(18, 9), nullable=False),
        sa.Column("equivalent_unit", sa.String(8), nullable=False),
        sa.Column("is_estimated", sa.Boolean(), nullable=False),
        sa.Column("source_type", sa.String(48), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("quantity > 0", name="ck_food_measures_positive_quantity"),
        sa.CheckConstraint("equivalent_quantity > 0", name="ck_food_measures_positive_equivalent"),
        sa.CheckConstraint(
            "equivalent_unit IN ('g', 'ml')", name="ck_food_measures_equivalent_unit"
        ),
    )
    op.create_index("ix_food_measures_food_id", "food_measures", ["food_id"])


def downgrade() -> None:
    op.drop_table("food_measures")
    op.drop_table("food_nutrients")
    op.drop_table("foods")
