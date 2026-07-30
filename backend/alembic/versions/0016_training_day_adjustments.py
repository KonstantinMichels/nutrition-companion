"""training day energy adjustments

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    json = postgresql.JSONB()
    op.create_table(
        "training_sessions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "owner_profile_id",
            uuid,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("planned_start_time", sa.Time()),
        sa.Column("sport_type", sa.String(32), nullable=False),
        sa.Column("session_type", sa.String(32), nullable=False),
        sa.Column("planned_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("perceived_intensity", sa.String(16), nullable=False),
        sa.Column("baseline_inclusion", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("note", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_training_session_owner_date", "training_sessions", ["owner_profile_id", "session_date"]
    )
    op.create_index(
        "ix_training_sessions_owner_profile_id", "training_sessions", ["owner_profile_id"]
    )
    op.create_index("ix_training_sessions_status", "training_sessions", ["status"])
    op.create_table(
        "training_adjustment_preferences",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "owner_profile_id",
            uuid,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("default_baseline_assessment_mode", sa.String(32), nullable=False),
        sa.Column(
            "explicit_assessment_id", uuid, sa.ForeignKey("assessments.id", ondelete="SET NULL")
        ),
        sa.Column("default_strategy", sa.String(32), nullable=False),
        sa.Column("positive_energy_cap_kcal", sa.Numeric(12, 4), nullable=False),
        sa.Column("negative_energy_cap_kcal", sa.Numeric(12, 4), nullable=False),
        sa.Column("relative_energy_cap", sa.Numeric(8, 6), nullable=False),
        sa.Column("carbohydrate_adjustments_enabled", sa.Boolean(), nullable=False),
        sa.Column("redistribution_enabled", sa.Boolean(), nullable=False),
        sa.Column("minimum_rest_day_target_kcal", sa.Numeric(12, 4)),
        sa.Column("include_cancelled_sessions", sa.Boolean(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_training_adjustment_preferences_owner_profile_id",
        "training_adjustment_preferences",
        ["owner_profile_id"],
    )
    op.create_index(
        "uq_training_preference_default",
        "training_adjustment_preferences",
        ["owner_profile_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true AND is_archived = false"),
    )
    op.create_table(
        "training_adjustment_batches",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "owner_profile_id",
            uuid,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column(
            "source_assessment_id",
            uuid,
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "preference_id",
            uuid,
            sa.ForeignKey("training_adjustment_preferences.id", ondelete="SET NULL"),
        ),
        sa.Column("iso_week_start", sa.Date()),
        sa.Column("single_date", sa.Date()),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("client_operation_id", uuid, nullable=False),
        sa.Column("preview_snapshot", json, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_training_adjustment_batches_owner_profile_id",
        "training_adjustment_batches",
        ["owner_profile_id"],
    )
    op.create_index(
        "ix_training_adjustment_batches_status", "training_adjustment_batches", ["status"]
    )
    op.create_index(
        "uq_training_adjustment_operation",
        "training_adjustment_batches",
        ["owner_profile_id", "client_operation_id"],
        unique=True,
    )
    op.create_table(
        "training_day_target_adjustments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "batch_id",
            uuid,
            sa.ForeignKey("training_adjustment_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_profile_id",
            uuid,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("adjustment_date", sa.Date(), nullable=False),
        sa.Column(
            "source_assessment_id",
            uuid,
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("load_category", sa.String(24), nullable=False),
        sa.Column("baseline_energy_target_kcal", sa.Numeric(14, 6), nullable=False),
        sa.Column("energy_delta_kcal", sa.Numeric(14, 6), nullable=False),
        sa.Column("adjusted_energy_target_kcal", sa.Numeric(14, 6), nullable=False),
        sa.Column("carbohydrate_delta_g", sa.Numeric(14, 6), nullable=False),
        sa.Column("baseline_carbohydrate_target_snapshot", json, nullable=False),
        sa.Column("adjusted_carbohydrate_target_snapshot", json, nullable=False),
        sa.Column("protein_target_snapshot", json, nullable=False),
        sa.Column("safety_validation_status", sa.String(24), nullable=False),
        sa.Column("calculation_metadata", json, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_training_adjustment_owner_date",
        "training_day_target_adjustments",
        ["owner_profile_id", "adjustment_date"],
    )
    op.create_index(
        "ix_training_day_target_adjustments_batch_id",
        "training_day_target_adjustments",
        ["batch_id"],
    )
    op.create_index(
        "uq_training_adjustment_active_date",
        "training_day_target_adjustments",
        ["owner_profile_id", "adjustment_date"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )
    op.add_column("daily_meal_plans", sa.Column("training_day_adjustment_id", uuid))
    op.create_index(
        "ix_daily_meal_plans_training_day_adjustment_id",
        "daily_meal_plans",
        ["training_day_adjustment_id"],
    )
    op.create_foreign_key(
        "fk_daily_plan_training_adjustment",
        "daily_meal_plans",
        "training_day_target_adjustments",
        ["training_day_adjustment_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_daily_plan_training_adjustment", "daily_meal_plans", type_="foreignkey")
    op.drop_index("ix_daily_meal_plans_training_day_adjustment_id", table_name="daily_meal_plans")
    op.drop_column("daily_meal_plans", "training_day_adjustment_id")
    op.drop_table("training_day_target_adjustments")
    op.drop_table("training_adjustment_batches")
    op.drop_table("training_adjustment_preferences")
    op.drop_table("training_sessions")
