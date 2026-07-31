"""add consumption tracking core

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

from alembic import op
from app.database.base import Base

# Import registers the five tables and their referenced metadata.
from app.modules.consumption_tracking import models as _models  # noqa: F401

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "consumption_days",
    "consumption_meals",
    "planned_entry_consumption_outcomes",
    "consumption_entries",
    "consumption_entry_nutrient_snapshots",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind, checkfirst=True)
