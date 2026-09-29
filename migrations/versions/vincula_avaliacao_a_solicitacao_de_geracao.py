"""Vincula avaliação de conhecimento à solicitação de geração."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_request",
        sa.Column("assessment_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_generation_request_assessment_id",
        "generation_request",
        "knowledge_assessment",
        ["assessment_id"],
        ["kas_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_generation_request_assessment_id",
        "generation_request",
        ["assessment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generation_request_assessment_id",
        table_name="generation_request",
    )
    op.drop_constraint(
        "fk_generation_request_assessment_id",
        "generation_request",
        type_="foreignkey",
    )
    op.drop_column("generation_request", "assessment_id")
