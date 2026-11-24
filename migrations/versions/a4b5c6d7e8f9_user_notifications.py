"""Adiciona notificações persistentes por usuário."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4b5c6d7e8f9"
down_revision: str | Sequence[str] | None = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.usr_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_key", sa.String(100), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("destination", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "user_id", "event_key", name="uq_notification_user_event"
        ),
    )
    op.create_index(
        "ix_notification_user_created",
        "notification",
        ["user_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_user_created", table_name="notification")
    op.drop_table("notification")
