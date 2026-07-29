"""extend automation preferences and audits for CP-SAT optimizer

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels = None
depends_on = None


PREFERENCE_COLUMNS = (
    sa.Column("optimizer_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column(
        "default_generation_engine",
        sa.String(40),
        nullable=False,
        server_default="optimizer_strict",
    ),
    sa.Column("solver_time_limit_day_seconds", sa.Integer(), nullable=False, server_default="5"),
    sa.Column("solver_time_limit_week_seconds", sa.Integer(), nullable=False, server_default="20"),
    sa.Column("solver_relative_gap_limit", sa.Numeric(8, 6), nullable=False, server_default="0.02"),
    sa.Column("solver_candidate_limit_per_slot", sa.Integer(), nullable=False, server_default="40"),
    sa.Column(
        "maximum_recipe_repetitions_per_day", sa.Integer(), nullable=False, server_default="2"
    ),
    sa.Column("strict_energy_target", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("strict_protein_minimum", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("strict_fiber_minimum", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("strict_fat_range", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column(
        "strict_saturated_fat_maximum", sa.Boolean(), nullable=False, server_default=sa.false()
    ),
    sa.Column(
        "strict_daily_preparation_time", sa.Boolean(), nullable=False, server_default=sa.false()
    ),
    sa.Column("maximum_daily_preparation_time_minutes", sa.Integer()),
    sa.Column("maximum_weekly_unique_shopping_items", sa.Integer()),
    sa.Column(
        "constraint_relaxation_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
    ),
    sa.Column("relaxable_constraint_priorities", sa.JSON(), nullable=False, server_default="{}"),
    sa.Column("objective_weights", sa.JSON(), nullable=False, server_default="{}"),
    sa.Column("meal_prep_preference", sa.String(24), nullable=False, server_default="neutral"),
    sa.Column("compare_with_greedy", sa.Boolean(), nullable=False, server_default=sa.true()),
)

APPLICATION_COLUMNS = (
    sa.Column("generation_engine", sa.String(40), nullable=False, server_default="greedy"),
    sa.Column("solver_status", sa.String(40)),
    sa.Column("solver_version", sa.String(40)),
    sa.Column("objective_value", sa.Numeric(30, 6)),
    sa.Column("relative_gap", sa.Numeric(12, 8)),
    sa.Column("relaxation_used", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("relaxation_summary", sa.JSON(), nullable=False, server_default="[]"),
    sa.Column("objective_summary", sa.JSON(), nullable=False, server_default="[]"),
    sa.Column("greedy_comparison_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
)


def upgrade() -> None:
    for column in PREFERENCE_COLUMNS:
        op.add_column("meal_plan_automation_preferences", column)
    for column in APPLICATION_COLUMNS:
        op.add_column("meal_plan_automation_applications", column)


def downgrade() -> None:
    for column in reversed(APPLICATION_COLUMNS):
        op.drop_column("meal_plan_automation_applications", column.name)
    for column in reversed(PREFERENCE_COLUMNS):
        op.drop_column("meal_plan_automation_preferences", column.name)
