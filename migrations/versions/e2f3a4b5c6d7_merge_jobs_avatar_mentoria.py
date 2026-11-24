"""Unifica as migrations de jobs, avatares e mentoria."""

from collections.abc import Sequence

revision: str = "e2f3a4b5c6d7"
down_revision: str | Sequence[str] | None = (
    "ba45c6d0fcbd",
    "d1e2f3a4b5c6",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
