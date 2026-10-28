"""Adiciona motivo da avaliação à resposta de quiz."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | Sequence[str] | None = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "answer",
        sa.Column("ans_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("answer", "ans_reason")
