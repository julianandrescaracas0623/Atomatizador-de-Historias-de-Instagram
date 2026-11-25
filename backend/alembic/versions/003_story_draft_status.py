"""add draft value to story_status

Revision ID: 003_story_draft_status
Revises: 002_publishing_started_at
Create Date: 2026-11-25
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_story_draft_status"
down_revision: Union[str, None] = "002_publishing_started_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE no puede correr dentro de una transacción en todas las versiones.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE story_status ADD VALUE IF NOT EXISTS 'draft'")


def downgrade() -> None:
    # Postgres no permite quitar valores de un enum sin recrearlo. Los borradores
    # NO pasan a pending: nunca se aprobaron, así que no deben publicarse.
    op.execute(
        "UPDATE scheduled_stories SET status = 'failed', "
        "error_message = 'Borrador revertido por migración; no aprobado' "
        "WHERE status = 'draft'"
    )
