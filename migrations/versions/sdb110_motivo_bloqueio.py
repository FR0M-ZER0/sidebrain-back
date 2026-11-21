"""Distingue os tipos de operação de privacidade pendente."""

from alembic import op
import sqlalchemy as sa

revision = "sdb110_reason"
down_revision = "sdb110_mentor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mentor_privacy_block", sa.Column("reason", sa.String(16), nullable=True)
    )
    op.create_check_constraint(
        "ck_mentor_privacy_block_reason",
        "mentor_privacy_block",
        "(blocked IS FALSE AND reason IS NULL) OR "
        "(blocked IS TRUE AND reason IS NOT NULL "
        "AND reason IN ('revocation', 'deletion'))",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_mentor_privacy_block_reason",
        "mentor_privacy_block",
        type_="check",
    )
    op.drop_column("mentor_privacy_block", "reason")
