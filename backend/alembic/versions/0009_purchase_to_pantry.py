"""add purchase-to-pantry handoffs

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopping_list_items",
        sa.Column(
            "pantry_handoff_state", sa.String(24), nullable=False, server_default="not_started"
        ),
    )
    op.add_column(
        "shopping_list_items",
        sa.Column(
            "pantry_transferred_quantity", sa.Numeric(30, 15), nullable=False, server_default="0"
        ),
    )
    op.create_table(
        "purchase_to_pantry_handoffs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("shopping_list_id", sa.Uuid(), nullable=False),
        sa.Column("shopping_list_name_snapshot", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("client_operation_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_purchase_handoff_operation"
        ),
    )
    op.create_index(
        "ix_purchase_to_pantry_handoffs_owner_profile_id",
        "purchase_to_pantry_handoffs",
        ["owner_profile_id"],
    )
    op.create_index(
        "ix_purchase_to_pantry_handoffs_shopping_list_id",
        "purchase_to_pantry_handoffs",
        ["shopping_list_id"],
    )
    op.create_index(
        "ix_purchase_handoff_list_created",
        "purchase_to_pantry_handoffs",
        ["shopping_list_id", "created_at"],
    )
    op.create_table(
        "purchase_to_pantry_handoff_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("handoff_id", sa.Uuid(), nullable=False),
        sa.Column("shopping_list_item_id", sa.Uuid(), nullable=False),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("shopping_item_name_snapshot", sa.String(200), nullable=False),
        sa.Column("planned_purchase_quantity", sa.Numeric(30, 15)),
        sa.Column("planned_purchase_unit", sa.String(32)),
        sa.Column("actual_transferred_quantity", sa.Numeric(30, 15), nullable=False),
        sa.Column("canonical_unit", sa.String(8), nullable=False),
        sa.Column("mark_item_handoff_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "actual_transferred_quantity > 0", name="purchase_handoff_item_positive_quantity"
        ),
        sa.ForeignKeyConstraint(
            ["handoff_id"], ["purchase_to_pantry_handoffs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["shopping_list_item_id"], ["shopping_list_items.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_to_pantry_handoff_items_handoff_id",
        "purchase_to_pantry_handoff_items",
        ["handoff_id"],
    )
    op.create_index(
        "ix_purchase_to_pantry_handoff_items_shopping_list_item_id",
        "purchase_to_pantry_handoff_items",
        ["shopping_list_item_id"],
    )
    op.create_index(
        "ix_purchase_handoff_item_shopping_item",
        "purchase_to_pantry_handoff_items",
        ["shopping_list_item_id", "created_at"],
    )
    op.create_table(
        "purchase_to_pantry_destinations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("handoff_item_id", sa.Uuid(), nullable=False),
        sa.Column("destination_type", sa.String(24), nullable=False),
        sa.Column("pantry_location_id", sa.Uuid(), nullable=False),
        sa.Column("target_stock_lot_id", sa.Uuid()),
        sa.Column("created_stock_lot_id", sa.Uuid()),
        sa.Column("pantry_movement_id", sa.Uuid(), nullable=False),
        sa.Column("entered_quantity", sa.Numeric(30, 15), nullable=False),
        sa.Column("entered_unit_code", sa.String(32), nullable=False),
        sa.Column("food_measure_id", sa.Uuid()),
        sa.Column("normalized_quantity", sa.Numeric(30, 15), nullable=False),
        sa.Column("normalized_unit", sa.String(8), nullable=False),
        sa.Column("conversion_estimated", sa.Boolean(), nullable=False),
        sa.Column("purchase_date", sa.Date()),
        sa.Column("opened_date", sa.Date()),
        sa.Column("best_before_date", sa.Date()),
        sa.Column("use_by_date", sa.Date()),
        sa.Column("note", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "destination_type IN ('new_stock_lot','existing_stock_lot')",
            name="purchase_destination_valid_type",
        ),
        sa.CheckConstraint(
            "normalized_quantity > 0", name="purchase_destination_positive_quantity"
        ),
        sa.ForeignKeyConstraint(
            ["handoff_item_id"], ["purchase_to_pantry_handoff_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pantry_location_id"], ["pantry_locations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_stock_lot_id"], ["pantry_stock_lots.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_stock_lot_id"], ["pantry_stock_lots.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["pantry_movement_id"], ["pantry_movements.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["food_measure_id"], ["food_measures.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_to_pantry_destinations_handoff_item_id",
        "purchase_to_pantry_destinations",
        ["handoff_item_id"],
    )


def downgrade() -> None:
    op.drop_table("purchase_to_pantry_destinations")
    op.drop_table("purchase_to_pantry_handoff_items")
    op.drop_table("purchase_to_pantry_handoffs")
    op.drop_column("shopping_list_items", "pantry_transferred_quantity")
    op.drop_column("shopping_list_items", "pantry_handoff_state")
