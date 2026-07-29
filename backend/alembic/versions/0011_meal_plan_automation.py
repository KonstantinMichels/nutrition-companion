"""add deterministic meal-plan automation preferences and audit

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meal_plan_automation_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("assessment_selection_mode", sa.String(32), nullable=False),
        sa.Column("selected_assessment_id", sa.Uuid()),
        sa.Column("generation_scope_default", sa.String(24), nullable=False),
        sa.Column("pantry_preference", sa.String(32), nullable=False),
        sa.Column("shopping_effort_preference", sa.String(40), nullable=False),
        sa.Column("maximum_recipe_repetitions_per_week", sa.Integer(), nullable=False),
        sa.Column("minimum_days_between_same_recipe", sa.Integer(), nullable=False),
        sa.Column("maximum_preparation_time_minutes", sa.Integer()),
        sa.Column("allow_incomplete_basic_nutrition", sa.Boolean(), nullable=False),
        sa.Column("allow_archived_recipe_candidates", sa.Boolean(), nullable=False),
        sa.Column("include_optional_recipe_ingredients", sa.Boolean(), nullable=False),
        sa.Column("enabled_recipe_tag_codes", sa.JSON(), nullable=False),
        sa.Column("excluded_recipe_tag_codes", sa.JSON(), nullable=False),
        sa.Column("excluded_recipe_ids", sa.JSON(), nullable=False),
        sa.Column("scoring_weights", sa.JSON(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["selected_assessment_id"], ["assessments.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meal_plan_automation_preferences_owner_profile_id",
        "meal_plan_automation_preferences",
        ["owner_profile_id"],
    )
    op.create_index(
        "ix_automation_preferences_owner_default",
        "meal_plan_automation_preferences",
        ["owner_profile_id", "is_default"],
    )
    op.create_table(
        "automation_meal_slot_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("automation_preferences_id", sa.Uuid(), nullable=False),
        sa.Column("slot_code", sa.String(48), nullable=False),
        sa.Column("meal_type", sa.String(32), nullable=False),
        sa.Column("custom_name", sa.String(200)),
        sa.Column("default_time", sa.Time()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("allowed_recipe_tag_codes", sa.JSON(), nullable=False),
        sa.Column("excluded_recipe_tag_codes", sa.JSON(), nullable=False),
        sa.Column("target_energy_share_min", sa.Numeric(8, 6)),
        sa.Column("target_energy_share_max", sa.Numeric(8, 6)),
        sa.Column("minimum_protein_g", sa.Numeric(12, 6)),
        sa.Column("maximum_preparation_time_minutes", sa.Integer()),
        sa.Column("portion_minimum", sa.Numeric(8, 4), nullable=False),
        sa.Column("portion_maximum", sa.Numeric(8, 4), nullable=False),
        sa.Column("portion_step", sa.Numeric(8, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["automation_preferences_id"],
            ["meal_plan_automation_preferences.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_slot_preferences_position",
        "automation_meal_slot_templates",
        ["automation_preferences_id", "position"],
    )
    op.create_table(
        "meal_plan_automation_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_profile_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(24), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("automation_preferences_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_ids", sa.JSON(), nullable=False),
        sa.Column("applied_references", sa.JSON(), nullable=False),
        sa.Column("applied_slot_count", sa.Integer(), nullable=False),
        sa.Column("client_operation_id", sa.Uuid(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["automation_preferences_id"],
            ["meal_plan_automation_preferences.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_automation_application_operation"
        ),
    )
    op.create_index(
        "ix_meal_plan_automation_applications_owner_profile_id",
        "meal_plan_automation_applications",
        ["owner_profile_id"],
    )


def downgrade() -> None:
    op.drop_table("meal_plan_automation_applications")
    op.drop_table("automation_meal_slot_templates")
    op.drop_table("meal_plan_automation_preferences")
