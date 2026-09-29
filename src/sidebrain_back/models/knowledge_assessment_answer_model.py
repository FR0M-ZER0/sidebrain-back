import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.knowledge_assessment_alternative_model import (
        KnowledgeAssessmentAlternative,
    )
    from sidebrain_back.models.knowledge_assessment_model import (
        KnowledgeAssessment,
    )
    from sidebrain_back.models.knowledge_assessment_question_model import (
        KnowledgeAssessmentQuestion,
    )


class KnowledgeAssessmentAnswer(Base):
    __tablename__ = "knowledge_assessment_answer"
    __table_args__ = (
        UniqueConstraint(
            "kar_assessment_id",
            "kar_question_id",
            name="uq_knowledge_assessment_answer_question",
        ),
        ForeignKeyConstraint(
            ["kar_question_id", "kar_assessment_id"],
            [
                "knowledge_assessment_question.kaq_id",
                "knowledge_assessment_question.kaq_assessment_id",
            ],
            name="fk_knowledge_assessment_answer_question_assessment",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["kar_alternative_id", "kar_question_id"],
            [
                "knowledge_assessment_alternative.kaa_id",
                "knowledge_assessment_alternative.kaa_question_id",
            ],
            name="fk_knowledge_assessment_answer_alternative_question",
            ondelete="CASCADE",
        ),
    )

    kar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kar_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_assessment.kas_id", ondelete="CASCADE"),
        nullable=False,
    )
    kar_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    kar_alternative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    kar_created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    assessment: Mapped["KnowledgeAssessment"] = relationship(
        back_populates="answers",
        foreign_keys=[kar_assessment_id],
    )
    question: Mapped["KnowledgeAssessmentQuestion"] = relationship(
        back_populates="answers",
        foreign_keys=[kar_question_id],
        overlaps="assessment,answers",
    )
    alternative: Mapped["KnowledgeAssessmentAlternative"] = relationship(
        back_populates="answers",
        foreign_keys=[kar_alternative_id],
        overlaps="question,answers",
    )
