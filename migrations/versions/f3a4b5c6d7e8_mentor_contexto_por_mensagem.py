"""Associa o contexto da tela à mensagem do estudante."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3a4b5c6d7e8"
down_revision: str | Sequence[str] | None = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mentor_message",
        sa.Column("context", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mentor_message", "context")
