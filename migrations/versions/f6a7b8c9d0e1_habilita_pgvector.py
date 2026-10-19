"""Habilita a extensão pgvector no banco da aplicação."""

from collections.abc import Sequence

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # A extensão pode ser preexistente e compartilhada por outros objetos.
    # O rollback preserva essa dependência de infraestrutura.
    pass
