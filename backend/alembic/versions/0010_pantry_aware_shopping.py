"""add pantry-aware shopping source identity and operations

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pantry_aware_shopping_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("target_shopping_list_id", sa.Uuid(), nullable=False),
        sa.Column("source_scope_type", sa.String(40), nullable=False),
        sa.Column("source_reference", sa.JSON(), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=False),
        sa.Column("pantry_date_mode", sa.String(40), nullable=False),
        sa.Column("other_open_lists_considered", sa.Boolean(), nullable=False),
        sa.Column("client_operation_id", sa.Uuid(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["target_shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_pantry_aware_operation"
        ),
    )
    op.create_index(
        "ix_pantry_aware_shopping_operations_owner_profile_id",
        "pantry_aware_shopping_operations",
        ["owner_profile_id"],
    )
    op.create_index(
        "ix_pantry_aware_shopping_operations_target_shopping_list_id",
        "pantry_aware_shopping_operations",
        ["target_shopping_list_id"],
    )
    op.create_index(
        "ix_pantry_aware_target_created",
        "pantry_aware_shopping_operations",
        ["target_shopping_list_id", "created_at"],
    )
    op.add_column("shopping_list_item_sources", sa.Column("source_identity", sa.String(500)))
    op.add_column("shopping_list_item_sources", sa.Column("source_version", sa.String(128)))
    op.add_column("shopping_list_item_sources", sa.Column("pantry_aware_operation_id", sa.Uuid()))
    op.add_column(
        "shopping_list_item_sources",
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_foreign_key(
        "fk_shopping_source_pantry_aware_operation",
        "shopping_list_item_sources",
        "pantry_aware_shopping_operations",
        ["pantry_aware_operation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_shopping_list_item_sources_pantry_aware_operation_id",
        "shopping_list_item_sources",
        ["pantry_aware_operation_id"],
    )
    op.create_index(
        "ix_shopping_source_identity", "shopping_list_item_sources", ["source_identity"]
    )


def downgrade() -> None:
    op.drop_index("ix_shopping_source_identity", table_name="shopping_list_item_sources")
    op.drop_index(
        "ix_shopping_list_item_sources_pantry_aware_operation_id",
        table_name="shopping_list_item_sources",
    )
    op.drop_constraint(
        "fk_shopping_source_pantry_aware_operation",
        "shopping_list_item_sources",
        type_="foreignkey",
    )
    op.drop_column("shopping_list_item_sources", "refreshed_at")
    op.drop_column("shopping_list_item_sources", "pantry_aware_operation_id")
    op.drop_column("shopping_list_item_sources", "source_version")
    op.drop_column("shopping_list_item_sources", "source_identity")
    op.drop_table("pantry_aware_shopping_operations")
