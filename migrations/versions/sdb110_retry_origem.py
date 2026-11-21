"""Registra a origem de novas tentativas de mentoria."""

from alembic import op
import sqlalchemy as sa

revision = "sdb110_retry"
down_revision = "sdb110_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mentor_generation",
        sa.Column("retry_of_generation_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_mentor_generation_retry_source",
        "mentor_generation",
        "mentor_generation",
        ["retry_of_generation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_mentor_generation_retry_source",
        "mentor_generation",
        type_="foreignkey",
    )
    op.drop_column("mentor_generation", "retry_of_generation_id")
