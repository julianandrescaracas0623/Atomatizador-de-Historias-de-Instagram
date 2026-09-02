"""initial users and scheduled_stories

Revision ID: 001_initial
Revises:
Create Date: 2026-08-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "scheduled_stories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column(
            "media_type",
            sa.Enum("image", "video", name="media_type"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "publishing", "published", "failed", name="story_status"),
            nullable=False,
        ),
        sa.Column("instagram_media_id", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scheduled_stories_status_scheduled", "scheduled_stories", ["status", "scheduled_at"])


def downgrade() -> None:
    op.drop_index("ix_scheduled_stories_status_scheduled", table_name="scheduled_stories")
    op.drop_table("scheduled_stories")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS story_status")
    op.execute("DROP TYPE IF EXISTS media_type")
