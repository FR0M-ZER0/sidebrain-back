"""Adiciona persistência para solicitações assíncronas de geração."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    generation_status = postgresql.ENUM(
        "pending",
        "succeeded",
        "failed",
        name="generation_status",
        create_type=False,
    )
    generation_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "generation_request",
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("context_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column(
            "knowledge_level",
            postgresql.ENUM(
                "beginner",
                "intermediate",
                "advanced",
                "pro",
                name="step_level",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("assessment_answers", sa.JSON(), nullable=True),
        sa.Column(
            "status", generation_status, server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("track_id", sa.UUID(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.usr_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["track.trk_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index("ix_generation_request_user_id", "generation_request", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_request_user_id", table_name="generation_request")
    op.drop_table("generation_request")
    postgresql.ENUM(name="generation_status").drop(op.get_bind(), checkfirst=True)