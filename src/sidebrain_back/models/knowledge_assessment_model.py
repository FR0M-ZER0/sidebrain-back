import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.enums.step_level_enum import StepLevelEnum

if TYPE_CHECKING:
    from sidebrain_back.models.knowledge_assessment_answer_model import (
        KnowledgeAssessmentAnswer,
    )
    from sidebrain_back.models.knowledge_assessment_question_model import (
        KnowledgeAssessmentQuestion,
    )
    from sidebrain_back.models.user_model import User


class KnowledgeAssessment(Base):
    __tablename__ = "knowledge_assessment"
    __table_args__ = (
        CheckConstraint(
            "kas_score IS NULL OR kas_score BETWEEN 0 AND 5",
            name="ck_knowledge_assessment_score_range",
        ),
        CheckConstraint(
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
        CheckConstraint(
            "kas_status <> 'completed' OR "
            "((kas_score BETWEEN 0 AND 1 AND kas_level = 'beginner') OR "
            "(kas_score BETWEEN 2 AND 3 AND kas_level = 'intermediate') OR "
            "(kas_score = 4 AND kas_level = 'advanced') OR "
            "(kas_score = 5 AND kas_level = 'pro'))",
            name="ck_knowledge_assessment_score_level",
        ),
        CheckConstraint(
            "kas_error_code IS NULL OR kas_error_code IN "
            "('generation_failed', 'invalid_generation_result')",
            name="ck_knowledge_assessment_public_error_code",
        ),
        Index(
            "uq_knowledge_assessment_active_context",
            "kas_user_id",
            "kas_context_fingerprint",
            unique=True,
            postgresql_where=text(
                "kas_status IN ('pending', 'generated')"
            ),
        ),
    )

    kas_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kas_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kas_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    kas_objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    kas_skip: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    kas_context_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    kas_status: Mapped[KnowledgeAssessmentStatusEnum] = mapped_column(
        ENUM(
            KnowledgeAssessmentStatusEnum,
            name="knowledge_assessment_status",
            create_type=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=KnowledgeAssessmentStatusEnum.PENDING,
        server_default=text("'pending'"),
    )
    kas_score: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    kas_level: Mapped[StepLevelEnum | None] = mapped_column(
        ENUM(
            StepLevelEnum,
            name="step_level",
            create_type=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=True,
    )
    kas_error_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    kas_created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    kas_updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    kas_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="knowledge_assessments")
    questions: Mapped[list["KnowledgeAssessmentQuestion"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="KnowledgeAssessmentQuestion.kaq_position.asc()",
    )
    answers: Mapped[list["KnowledgeAssessmentAnswer"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        foreign_keys="KnowledgeAssessmentAnswer.kar_assessment_id",
        order_by="KnowledgeAssessmentAnswer.kar_created_at.asc()",
    )

    def __repr__(self) -> str:
        return (
            "<KnowledgeAssessment "
            f"kas_id={self.kas_id} status={self.kas_status}>"
        )
