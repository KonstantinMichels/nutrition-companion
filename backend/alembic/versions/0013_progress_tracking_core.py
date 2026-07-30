"""add progress tracking observations and goals

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels = None
depends_on = None


def _common(name: str) -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("observed_time", sa.Time()),
        sa.Column("source_type", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("note", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "body_weight_observations",
        *_common("weight"),
        sa.Column("normalized_weight_kg", sa.Numeric(15, 8), nullable=False),
        sa.Column("entered_weight", sa.Numeric(15, 8), nullable=False),
        sa.Column("entered_unit", sa.String(8), nullable=False),
        sa.Column(
            "measurement_context", sa.String(24), nullable=False, server_default="unspecified"
        ),
        sa.Column(
            "unusual_change_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index(
        "ix_progress_weight_profile_date",
        "body_weight_observations",
        ["owner_profile_id", "observed_on"],
    )
    op.create_table(
        "body_measurement_observations",
        *_common("measurement"),
        sa.Column("measurement_type", sa.String(32), nullable=False),
        sa.Column("normalized_value_cm", sa.Numeric(10, 4), nullable=False),
        sa.Column("entered_value", sa.Numeric(12, 4), nullable=False),
        sa.Column("entered_unit", sa.String(8), nullable=False),
        sa.Column(
            "measurement_method", sa.String(32), nullable=False, server_default="unspecified"
        ),
    )
    op.create_index(
        "ix_progress_measurement_profile_date",
        "body_measurement_observations",
        ["owner_profile_id", "observed_on"],
    )
    op.create_index(
        "ix_progress_measurement_profile_type",
        "body_measurement_observations",
        ["owner_profile_id", "measurement_type"],
    )
    op.create_table(
        "body_composition_observations",
        *_common("composition"),
        sa.Column("body_fat_percent", sa.Numeric(7, 3)),
        sa.Column("lean_mass_kg", sa.Numeric(9, 4)),
        sa.Column("fat_mass_kg", sa.Numeric(9, 4)),
        sa.Column("measurement_method", sa.String(40), nullable=False),
        sa.Column("device_name", sa.String(200)),
    )
    op.create_index(
        "ix_progress_composition_profile_date",
        "body_composition_observations",
        ["owner_profile_id", "observed_on"],
    )
    op.create_table(
        "progress_goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("goal_type", sa.String(24), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("start_weight_kg", sa.Numeric(9, 4)),
        sa.Column(
            "start_observation_id",
            sa.Uuid(),
            sa.ForeignKey("body_weight_observations.id", ondelete="SET NULL"),
        ),
        sa.Column("target_weight_kg", sa.Numeric(9, 4)),
        sa.Column("target_weight_min_kg", sa.Numeric(9, 4)),
        sa.Column("target_weight_max_kg", sa.Numeric(9, 4)),
        sa.Column("target_date", sa.Date()),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("note", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_progress_goals_owner_profile_id", "progress_goals", ["owner_profile_id"])
    op.create_index(
        "ix_progress_goal_one_active",
        "progress_goals",
        ["owner_profile_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_table("progress_goals")
    op.drop_table("body_composition_observations")
    op.drop_table("body_measurement_observations")
    op.drop_table("body_weight_observations")
