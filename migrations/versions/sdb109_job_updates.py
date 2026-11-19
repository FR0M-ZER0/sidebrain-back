"""Adiciona persistencia e notificacoes para acompanhamento de jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "sdb109jobupdates"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "step_preparation",
        sa.Column("task_id", sa.String(255), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.usr_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "track_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("track.trk_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_step_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("step.stp_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_step_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("step.stp_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_step_preparation_status",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND finished_at IS NULL) OR "
            "(status IN ('completed', 'failed') AND finished_at IS NOT NULL)",
            name="ck_step_preparation_finished_at",
        ),
    )
    op.create_index(
        "ix_step_preparation_finished_at",
        "step_preparation",
        ["finished_at"],
    )
    op.create_table(
        "step_summary_generation",
        sa.Column(
            "step_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("step.stp_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.CheckConstraint(
            "generation > 0", name="ck_step_summary_generation"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_step_summary_generation_status",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION notify_job_update() RETURNS trigger AS $$
        DECLARE payload text;
        BEGIN
          IF TG_TABLE_NAME = 'generation_request' THEN
            payload := 'track_generation:' || NEW.request_id::text;
          ELSIF TG_TABLE_NAME = 'knowledge_assessment' THEN
            payload := 'assessment:' || NEW.kas_id::text;
          ELSIF TG_TABLE_NAME = 'step_preparation' THEN
            payload := 'step_preparation:' || NEW.task_id;
          ELSE
            SELECT 'step_summary:' || stp_track_id::text || ':' || stp_id::text
              INTO payload FROM step WHERE stp_id = NEW.step_id;
          END IF;
          PERFORM pg_notify('sidebrain_job_updates', payload);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "generation_request",
        "knowledge_assessment",
        "step_preparation",
        "step_summary_generation",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_job_update "
            f"AFTER INSERT OR UPDATE ON {table} FOR EACH ROW "
            "EXECUTE FUNCTION notify_job_update()"
        )


def downgrade() -> None:
    for table in (
        "generation_request",
        "knowledge_assessment",
        "step_preparation",
        "step_summary_generation",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_job_update ON {table}")
    op.execute("DROP FUNCTION IF EXISTS notify_job_update()")
    op.drop_table("step_summary_generation")
    op.drop_index(
        "ix_step_preparation_finished_at", table_name="step_preparation"
    )
    op.drop_table("step_preparation")
