"""add pantry core

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pantry_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location_type", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="pantry_location_nonnegative_position"),
        sa.CheckConstraint(
            "location_type IN ('pantry','refrigerator','freezer','kitchen','cellar','other')",
            name="pantry_location_valid_type",
        ),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pantry_locations_owner_profile_id", "pantry_locations", ["owner_profile_id"]
    )
    op.create_index(
        "ix_pantry_location_owner_active_position",
        "pantry_locations",
        ["owner_profile_id", "is_archived", "position"],
    )
    op.create_table(
        "pantry_stock_lots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("current_quantity", sa.Numeric(30, 15), nullable=False),
        sa.Column("normalized_unit", sa.String(8), nullable=False),
        sa.Column("initial_entered_quantity", sa.Numeric(30, 15), nullable=False),
        sa.Column("initial_entered_unit_code", sa.String(32), nullable=False),
        sa.Column("initial_food_measure_id", sa.Uuid(), nullable=True),
        sa.Column(
            "initial_conversion_estimated", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("opened_date", sa.Date(), nullable=True),
        sa.Column("best_before_date", sa.Date(), nullable=True),
        sa.Column("use_by_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("is_depleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("depleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("current_quantity >= 0", name="pantry_lot_nonnegative_quantity"),
        sa.CheckConstraint(
            "initial_entered_quantity > 0", name="pantry_lot_positive_initial_quantity"
        ),
        sa.CheckConstraint("normalized_unit IN ('g','ml')", name="pantry_lot_valid_unit"),
        sa.CheckConstraint("version >= 1", name="pantry_lot_positive_version"),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["location_id"], ["pantry_locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["initial_food_measure_id"], ["food_measures.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_pantry_stock_lots_owner_profile_id", ["owner_profile_id"]),
        ("ix_pantry_stock_lots_food_id", ["food_id"]),
        ("ix_pantry_stock_lots_location_id", ["location_id"]),
        (
            "ix_pantry_lot_owner_active_food",
            ["owner_profile_id", "is_archived", "is_depleted", "food_id"],
        ),
        ("ix_pantry_lot_owner_location", ["owner_profile_id", "location_id"]),
        ("ix_pantry_lot_dates", ["best_before_date", "use_by_date"]),
    ):
        op.create_index(name, "pantry_stock_lots", columns)
    op.create_table(
        "pantry_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("stock_lot_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(40), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(30, 15), nullable=False),
        sa.Column("normalized_unit", sa.String(8), nullable=False),
        sa.Column("balance_before", sa.Numeric(30, 15), nullable=False),
        sa.Column("balance_after", sa.Numeric(30, 15), nullable=False),
        sa.Column("entered_quantity", sa.Numeric(30, 15), nullable=True),
        sa.Column("entered_unit_code", sa.String(32), nullable=True),
        sa.Column("food_measure_id", sa.Uuid(), nullable=True),
        sa.Column("conversion_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("target_location_id", sa.Uuid(), nullable=True),
        sa.Column("related_stock_lot_id", sa.Uuid(), nullable=True),
        sa.Column("client_operation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("normalized_unit IN ('g','ml')", name="pantry_movement_valid_unit"),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_lot_id"], ["pantry_stock_lots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_measure_id"], ["food_measures.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["target_location_id"], ["pantry_locations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["related_stock_lot_id"], ["pantry_stock_lots.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_profile_id",
            "client_operation_id",
            "movement_type",
            name="uq_pantry_movement_operation_type",
        ),
    )
    op.create_index(
        "ix_pantry_movements_owner_profile_id", "pantry_movements", ["owner_profile_id"]
    )
    op.create_index("ix_pantry_movements_stock_lot_id", "pantry_movements", ["stock_lot_id"])
    op.create_index(
        "ix_pantry_movement_lot_created", "pantry_movements", ["stock_lot_id", "created_at"]
    )
    op.create_index(
        "ix_pantry_movement_owner_operation",
        "pantry_movements",
        ["owner_profile_id", "client_operation_id"],
    )


def downgrade() -> None:
    op.drop_table("pantry_movements")
    op.drop_table("pantry_stock_lots")
    op.drop_table("pantry_locations")
