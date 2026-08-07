"""pantry consumption reconciliation

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

from alembic import op
from app.database.base import Base
from app.modules.consumption_tracking import models as _consumption_models  # noqa: F401
from app.modules.pantry_consumption_reconciliation import (
    models as _reconciliation_models,  # noqa: F401
)

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "consumption_recipe_ingredient_snapshots",
    "pantry_consumption_reconciliation_batches",
    "pantry_consumption_requirements",
    "pantry_consumption_allocations",
    "pantry_consumption_reversals",
    "pantry_consumption_reversal_allocations",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind, checkfirst=True)
