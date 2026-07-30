"""link assessment weights to progress observations

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "body_weight_observations",
        sa.Column(
            "source_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("assessments.id", ondelete="SET NULL"),
        ),
    )
    op.create_index(
        "uq_progress_weight_source_assessment",
        "body_weight_observations",
        ["source_assessment_id"],
        unique=True,
    )
    # Existing immutable assessments contain the kg value actually used by the
    # engine. Reuse the assessment UUID as the observation UUID so the backfill
    # remains deterministic and idempotent without a database UUID extension.
    op.execute(
        sa.text(
            """
            INSERT INTO body_weight_observations (
                id, owner_profile_id, observed_on, observed_time,
                normalized_weight_kg, entered_weight, entered_unit,
                source_type, source_assessment_id, measurement_context,
                note, unusual_change_confirmed, version, created_at, updated_at
            )
            SELECT
                a.id,
                a.profile_id,
                (a.calculated_at AT TIME ZONE 'Europe/Berlin')::date,
                (a.calculated_at AT TIME ZONE 'Europe/Berlin')::time,
                (a.input_snapshot #>> '{engine_input,weight_kg}')::numeric,
                (a.input_snapshot #>> '{engine_input,weight_kg}')::numeric,
                'kg',
                'assessment',
                a.id,
                'unspecified',
                NULL,
                false,
                1,
                a.calculated_at,
                a.calculated_at
            FROM assessments a
            WHERE a.input_snapshot #>> '{engine_input,weight_kg}' IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM body_weight_observations w
                  WHERE w.source_assessment_id = a.id OR w.id = a.id
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM body_weight_observations WHERE source_type = 'assessment'"))
    op.drop_index("uq_progress_weight_source_assessment", table_name="body_weight_observations")
    op.drop_column("body_weight_observations", "source_assessment_id")
