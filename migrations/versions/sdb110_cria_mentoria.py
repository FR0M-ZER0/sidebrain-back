"""Cria estruturas de mentoria por IA."""

from alembic import op
import sqlalchemy as sa

revision = "sdb110_mentor"
down_revision = "a92b8c9d0e1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mentor_consent",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id", sa.UUID(),
            sa.ForeignKey("user.usr_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("notice_version", sa.String(64), nullable=False),
        sa.Column("granted_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "purpose", name="uq_mentor_consent_user"),
    )
    op.create_index("ix_mentor_consent_user_id", "mentor_consent", ["user_id"])
    op.create_table(
        "mentor_conversation",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id", sa.UUID(),
            sa.ForeignKey("user.usr_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "track_id", sa.UUID(),
            sa.ForeignKey("track.trk_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mentor_conversation_track_id", "mentor_conversation", ["track_id"])
    op.create_index("ix_mentor_conversation_user_updated", "mentor_conversation", ["user_id", "updated_at"])
    op.create_table(
        "mentor_message",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "conversation_id", sa.UUID(),
            sa.ForeignKey("mentor_conversation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("generation_id", sa.UUID(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_mentor_message_sequence"),
        sa.UniqueConstraint("generation_id", name="uq_mentor_message_generation"),
        sa.CheckConstraint("role IN ('student', 'mentor')", name="ck_mentor_role"),
        sa.CheckConstraint("sequence > 0", name="ck_mentor_message_sequence"),
        sa.CheckConstraint("length(trim(content)) > 0", name="ck_mentor_content"),
        sa.CheckConstraint(
            "(role = 'student' AND generation_id IS NULL) OR "
            "(role = 'mentor' AND generation_id IS NOT NULL)",
            name="ck_mentor_message_generation_role",
        ),
        sa.CheckConstraint(
            "role <> 'student' OR length(content) <= 4000",
            name="ck_mentor_student_content_length",
        ),
    )
    op.create_index("ix_mentor_message_conversation_id", "mentor_message", ["conversation_id"])
    op.create_table(
        "mentor_generation",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "conversation_id", sa.UUID(),
            sa.ForeignKey("mentor_conversation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_message_id", sa.UUID(),
            sa.ForeignKey("mentor_message.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("attempt_id", sa.UUID(), nullable=True),
        sa.Column("attempt_deadline", sa.DateTime(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("conversation_id", "idempotency_key", name="uq_mentor_generation_idempotency"),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_mentor_generation_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_mentor_attempt_count"),
    )
    op.create_index("ix_mentor_generation_conversation_id", "mentor_generation", ["conversation_id"])
    op.create_index(
        "uq_mentor_generation_active", "mentor_generation", ["conversation_id"],
        unique=True, postgresql_where=sa.text("status IN ('queued', 'processing')"),
    )
    op.create_foreign_key(
        "fk_mentor_message_generation", "mentor_message", "mentor_generation",
        ["generation_id"], ["id"], ondelete="CASCADE",
    )
    op.create_table(
        "mentor_dispatch",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "generation_id", sa.UUID(),
            sa.ForeignKey("mentor_generation.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column("dispatched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "mentor_send_reservation",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id", sa.UUID(),
            sa.ForeignKey("user.usr_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "generation_id", sa.UUID(),
            sa.ForeignKey("mentor_generation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("attempt_id", name="uq_mentor_reservation_attempt"),
        sa.CheckConstraint("status IN ('in_flight', 'finished')", name="ck_mentor_reservation_status"),
    )
    op.create_index("ix_mentor_send_reservation_user_id", "mentor_send_reservation", ["user_id"])
    op.create_index("ix_mentor_send_reservation_generation_id", "mentor_send_reservation", ["generation_id"])
    op.create_table(
        "mentor_privacy_block",
        sa.Column(
            "user_id", sa.UUID(),
            sa.ForeignKey("user.usr_id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mentor_privacy_block")
    op.drop_table("mentor_send_reservation")
    op.drop_table("mentor_dispatch")
    op.drop_constraint(
        "fk_mentor_message_generation", "mentor_message", type_="foreignkey"
    )
    op.drop_table("mentor_generation")
    op.drop_table("mentor_message")
    op.drop_table("mentor_conversation")
    op.drop_table("mentor_consent")
