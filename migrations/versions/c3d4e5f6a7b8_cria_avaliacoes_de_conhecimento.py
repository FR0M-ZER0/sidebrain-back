"""Cria avaliações de conhecimento persistentes.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    assessment_status = postgresql.ENUM(
        "pending",
        "generated",
        "skipped",
        "completed",
        "failed",
        name="knowledge_assessment_status",
        create_type=False,
    )
    assessment_status.create(op.get_bind(), checkfirst=True)
    step_level = postgresql.ENUM(
        "beginner",
        "intermediate",
        "advanced",
        "pro",
        name="step_level",
        create_type=False,
    )

    op.create_table(
        "knowledge_assessment",
        sa.Column("kas_id", sa.UUID(), nullable=False),
        sa.Column("kas_user_id", sa.UUID(), nullable=False),
        sa.Column("kas_subject", sa.String(length=255), nullable=False),
        sa.Column("kas_objective", sa.Text(), nullable=True),
        sa.Column(
            "kas_skip",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "kas_context_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "kas_status",
            assessment_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("kas_score", sa.SmallInteger(), nullable=True),
        sa.Column("kas_level", step_level, nullable=True),
        sa.Column("kas_error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "kas_created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "kas_updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("kas_completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "kas_score IS NULL OR kas_score BETWEEN 0 AND 5",
            name="ck_knowledge_assessment_score_range",
        ),
        sa.CheckConstraint(
            "(kas_status IN ('pending', 'generated') "
            "AND kas_score IS NULL AND kas_level IS NULL "
            "AND kas_error_code IS NULL AND kas_completed_at IS NULL) OR "
            "(kas_status = 'skipped' AND kas_skip IS true "
            "AND kas_score IS NULL AND kas_level = 'beginner' "
            "AND kas_error_code IS NULL AND kas_completed_at IS NOT NULL) OR "
            "(kas_status = 'completed' AND kas_score IS NOT NULL "
            "AND kas_level IS NOT NULL AND kas_error_code IS NULL "
            "AND kas_completed_at IS NOT NULL) OR "
            "(kas_status = 'failed' AND kas_score IS NULL "
            "AND kas_level IS NULL AND kas_error_code IS NOT NULL "
            "AND kas_completed_at IS NULL)",
            name="ck_knowledge_assessment_state",
        ),
        sa.CheckConstraint(
            "kas_status <> 'completed' OR "
            "((kas_score BETWEEN 0 AND 1 AND kas_level = 'beginner') OR "
            "(kas_score BETWEEN 2 AND 3 AND kas_level = 'intermediate') OR "
            "(kas_score = 4 AND kas_level = 'advanced') OR "
            "(kas_score = 5 AND kas_level = 'pro'))",
            name="ck_knowledge_assessment_score_level",
        ),
        sa.CheckConstraint(
            "kas_error_code IS NULL OR kas_error_code IN "
            "('generation_failed', 'invalid_generation_result')",
            name="ck_knowledge_assessment_public_error_code",
        ),
        sa.ForeignKeyConstraint(
            ["kas_user_id"], ["user.usr_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("kas_id"),
    )
    op.create_index(
        "ix_knowledge_assessment_user_id",
        "knowledge_assessment",
        ["kas_user_id"],
    )
    op.create_index(
        "uq_knowledge_assessment_active_context",
        "knowledge_assessment",
        ["kas_user_id", "kas_context_fingerprint"],
        unique=True,
        postgresql_where=sa.text(
            "kas_status IN ('pending', 'generated')"
        ),
    )

    op.create_table(
        "knowledge_assessment_question",
        sa.Column("kaq_id", sa.UUID(), nullable=False),
        sa.Column("kaq_assessment_id", sa.UUID(), nullable=False),
        sa.Column("kaq_statement", sa.Text(), nullable=False),
        sa.Column("kaq_position", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "kaq_position BETWEEN 1 AND 5",
            name="ck_knowledge_assessment_question_position",
        ),
        sa.CheckConstraint(
            "length(btrim(kaq_statement)) > 0",
            name="ck_knowledge_assessment_question_statement",
        ),
        sa.ForeignKeyConstraint(
            ["kaq_assessment_id"],
            ["knowledge_assessment.kas_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("kaq_id"),
        sa.UniqueConstraint(
            "kaq_assessment_id",
            "kaq_position",
            name="uq_knowledge_assessment_question_position",
        ),
        sa.UniqueConstraint(
            "kaq_id",
            "kaq_assessment_id",
            name="uq_knowledge_assessment_question_assessment",
        ),
    )

    op.create_table(
        "knowledge_assessment_alternative",
        sa.Column("kaa_id", sa.UUID(), nullable=False),
        sa.Column("kaa_question_id", sa.UUID(), nullable=False),
        sa.Column("kaa_text", sa.Text(), nullable=False),
        sa.Column("kaa_position", sa.SmallInteger(), nullable=False),
        sa.Column(
            "kaa_is_correct",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kaa_position BETWEEN 1 AND 4",
            name="ck_knowledge_assessment_alternative_position",
        ),
        sa.CheckConstraint(
            "length(btrim(kaa_text)) > 0",
            name="ck_knowledge_assessment_alternative_text",
        ),
        sa.ForeignKeyConstraint(
            ["kaa_question_id"],
            ["knowledge_assessment_question.kaq_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("kaa_id"),
        sa.UniqueConstraint(
            "kaa_question_id",
            "kaa_position",
            name="uq_knowledge_assessment_alternative_position",
        ),
        sa.UniqueConstraint(
            "kaa_id",
            "kaa_question_id",
            name="uq_knowledge_assessment_alternative_question",
        ),
    )
    op.create_index(
        "uq_knowledge_assessment_alternative_correct",
        "knowledge_assessment_alternative",
        ["kaa_question_id"],
        unique=True,
        postgresql_where=sa.text("kaa_is_correct IS true"),
    )

    op.create_table(
        "knowledge_assessment_answer",
        sa.Column("kar_id", sa.UUID(), nullable=False),
        sa.Column("kar_assessment_id", sa.UUID(), nullable=False),
        sa.Column("kar_question_id", sa.UUID(), nullable=False),
        sa.Column("kar_alternative_id", sa.UUID(), nullable=False),
        sa.Column(
            "kar_created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["kar_assessment_id"],
            ["knowledge_assessment.kas_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["kar_question_id", "kar_assessment_id"],
            [
                "knowledge_assessment_question.kaq_id",
                "knowledge_assessment_question.kaq_assessment_id",
            ],
            name="fk_knowledge_assessment_answer_question_assessment",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["kar_alternative_id", "kar_question_id"],
            [
                "knowledge_assessment_alternative.kaa_id",
                "knowledge_assessment_alternative.kaa_question_id",
            ],
            name="fk_knowledge_assessment_answer_alternative_question",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("kar_id"),
        sa.UniqueConstraint(
            "kar_assessment_id",
            "kar_question_id",
            name="uq_knowledge_assessment_answer_question",
        ),
    )


def downgrade() -> None:
    op.drop_table("knowledge_assessment_answer")
    op.drop_index(
        "uq_knowledge_assessment_alternative_correct",
        table_name="knowledge_assessment_alternative",
    )
    op.drop_table("knowledge_assessment_alternative")
    op.drop_table("knowledge_assessment_question")
    op.drop_index(
        "uq_knowledge_assessment_active_context",
        table_name="knowledge_assessment",
    )
    op.drop_index(
        "ix_knowledge_assessment_user_id",
        table_name="knowledge_assessment",
    )
    op.drop_table("knowledge_assessment")
    postgresql.ENUM(name="knowledge_assessment_status").drop(
        op.get_bind(), checkfirst=True
    )
