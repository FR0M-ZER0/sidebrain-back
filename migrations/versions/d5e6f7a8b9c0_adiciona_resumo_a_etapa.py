"""Adiciona resumo das avaliações à etapa."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("step", sa.Column("stp_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("step", "stp_summary")
