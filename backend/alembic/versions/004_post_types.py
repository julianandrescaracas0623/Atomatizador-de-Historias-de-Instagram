"""add post_type, caption and extra_filenames to scheduled_stories

Revision ID: 004_post_types
Revises: 003_story_draft_status
Create Date: 2026-11-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_post_types"
down_revision: Union[str, None] = "003_story_draft_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

post_type_enum = postgresql.ENUM("story", "feed", "reel", "carousel", name="post_type", create_type=False)


def upgrade() -> None:
    post_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "scheduled_stories",
        sa.Column("post_type", post_type_enum, nullable=False, server_default="story"),
    )
    op.add_column(
        "scheduled_stories",
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "scheduled_stories",
        sa.Column("extra_filenames", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("scheduled_stories", "extra_filenames")
    op.drop_column("scheduled_stories", "caption")
    op.drop_column("scheduled_stories", "post_type")
    post_type_enum.drop(op.get_bind(), checkfirst=True)
