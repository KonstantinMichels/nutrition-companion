"""dynamic energy calibration

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "energy_calibration_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("adherence", sa.String(16), nullable=False),
        sa.Column("context_stability", sa.String(24), nullable=False),
        sa.Column("proposed_adjustment_kcal_per_day", sa.Numeric(12, 4)),
        sa.Column("accepted_adjustment_kcal_per_day", sa.Numeric(12, 4)),
        sa.Column("evidence_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("proposal_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rules_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "owner_profile_id", "client_operation_id", name="uq_energy_calibration_operation"
        ),
    )
    op.create_index(
        "ix_energy_calibration_records_owner_profile_id",
        "energy_calibration_records",
        ["owner_profile_id"],
    )
    op.add_column(
        "assessments", sa.Column("derived_from_assessment_id", postgresql.UUID(as_uuid=True))
    )
    op.add_column("assessments", sa.Column("derivation_type", sa.String(40)))
    op.add_column(
        "assessments", sa.Column("energy_calibration_record_id", postgresql.UUID(as_uuid=True))
    )
    op.add_column(
        "assessments", sa.Column("energy_calibration_adjustment_kcal_per_day", sa.Numeric(12, 4))
    )
    op.create_foreign_key(
        "fk_assessment_derived_from",
        "assessments",
        "assessments",
        ["derived_from_assessment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_assessment_energy_calibration",
        "assessments",
        "energy_calibration_records",
        ["energy_calibration_record_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_assessment_energy_calibration", "assessments", type_="foreignkey")
    op.drop_constraint("fk_assessment_derived_from", "assessments", type_="foreignkey")
    for name in (
        "energy_calibration_adjustment_kcal_per_day",
        "energy_calibration_record_id",
        "derivation_type",
        "derived_from_assessment_id",
    ):
        op.drop_column("assessments", name)
    op.drop_index(
        "ix_energy_calibration_records_owner_profile_id", table_name="energy_calibration_records"
    )
    op.drop_table("energy_calibration_records")
