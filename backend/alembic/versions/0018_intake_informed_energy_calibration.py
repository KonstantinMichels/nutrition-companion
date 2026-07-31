"""intake-informed energy calibration

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.database.base import Base
from app.modules.energy_calibration import models as _models  # noqa: F401

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("energy_calibration_records", sa.Column("method", sa.String(32), nullable=True))
    op.execute(
        "UPDATE energy_calibration_records SET method = 'target_response_proxy' "
        "WHERE method IS NULL"
    )
    op.alter_column("energy_calibration_records", "method", nullable=False)
    op.create_index(
        "ix_energy_calibration_records_method",
        "energy_calibration_records",
        ["owner_profile_id", "method", "created_at"],
    )
    bind = op.get_bind()
    for name in ("energy_calibration_consumption_days", "energy_calibration_weight_observations"):
        Base.metadata.tables[name].create(bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for name in ("energy_calibration_weight_observations", "energy_calibration_consumption_days"):
        Base.metadata.tables[name].drop(bind, checkfirst=True)
    op.drop_index("ix_energy_calibration_records_method", table_name="energy_calibration_records")
    op.drop_column("energy_calibration_records", "method")
