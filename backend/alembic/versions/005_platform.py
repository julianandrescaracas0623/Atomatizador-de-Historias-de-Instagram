"""add platform to scheduled_stories (instagram or linkedin)

Revision ID: 005_platform
Revises: 004_post_types
Create Date: 2026-11-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_platform"
down_revision: Union[str, None] = "004_post_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

platform_enum = postgresql.ENUM("instagram", "linkedin", name="platform", create_type=False)


def upgrade() -> None:
    platform_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "scheduled_stories",
        sa.Column("platform", platform_enum, nullable=False, server_default="instagram"),
    )


def downgrade() -> None:
    # Sin este paso, un borrador o programado de LinkedIn quedaría como post de Instagram
    # y el worker lo publicaría en Instagram. Se marca como fallido antes de perder la columna.
    op.execute(
        """
        UPDATE scheduled_stories
        SET status = 'failed',
            error_message = 'Revertido por migración: era de LinkedIn y no puede publicarse en Instagram'
        WHERE platform = 'linkedin' AND status IN ('draft', 'pending')
        """
    )
    op.drop_column("scheduled_stories", "platform")
    platform_enum.drop(op.get_bind(), checkfirst=True)
