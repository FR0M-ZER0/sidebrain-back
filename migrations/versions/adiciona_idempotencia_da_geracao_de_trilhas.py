"""Adiciona idempotência à geração de trilhas."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "16fd0aac0bc2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "track",
        sa.Column("trk_generation_request_id", sa.UUID(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_track_generation_request_id", "track", ["trk_generation_request_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_track_generation_request_id", "track", type_="unique")
    op.drop_column("track", "trk_generation_request_id")