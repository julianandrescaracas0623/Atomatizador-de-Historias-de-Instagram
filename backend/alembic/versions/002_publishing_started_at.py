"""add publishing_started_at to scheduled_stories

Revision ID: 002_publishing_started_at
Revises: 001_initial
Create Date: 2026-11-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_publishing_started_at"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scheduled_stories",
        sa.Column("publishing_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheduled_stories", "publishing_started_at")
