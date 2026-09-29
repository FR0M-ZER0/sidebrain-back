"""Adiciona ícone às trilhas."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "track",
        sa.Column("trk_icon", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("track", "trk_icon")
