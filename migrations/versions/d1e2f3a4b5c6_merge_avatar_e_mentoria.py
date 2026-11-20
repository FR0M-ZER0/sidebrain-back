"""Unifica as migrations de avatares e mentoria."""

from collections.abc import Sequence

revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = (
    "c0d1e2f3a4b5",
    "sdb110_retry",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
