"""Garante a coluna de resumo da etapa em bancos já
marcados como atualizados."""

from collections.abc import Sequence

from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE step "
        "ADD COLUMN IF NOT EXISTS stp_summary TEXT NULL"
    )


def downgrade() -> None:
    pass
