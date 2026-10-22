"""Unifica as migrations de RAG e autenticação."""

from collections.abc import Sequence

revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = (
    "a2b3c4d5e6f7",
    "f81a1b2c3d4",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
