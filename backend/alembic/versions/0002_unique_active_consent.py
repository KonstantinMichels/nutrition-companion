"""allow only one active consent per profile, purpose and text version

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_consent_active_profile_purpose_version",
        "consent_records",
        ["profile_id", "purpose_code", "consent_text_version"],
        unique=True,
        postgresql_where=sa.text("status = 'granted' AND withdrawn_at IS NULL"),
        sqlite_where=sa.text("status = 'granted' AND withdrawn_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_consent_active_profile_purpose_version",
        table_name="consent_records",
    )
