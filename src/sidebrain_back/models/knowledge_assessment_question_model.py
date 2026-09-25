import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.knowledge_assessment_alternative_model import (
        KnowledgeAssessmentAlternative,
    )
    from sidebrain_back.models.knowledge_assessment_answer_model import (
        KnowledgeAssessmentAnswer,
    )
    from sidebrain_back.models.knowledge_assessment_model import (
        KnowledgeAssessment,
    )


class KnowledgeAssessmentQuestion(Base):
    __tablename__ = "knowledge_assessment_question"
    __table_args__ = (
        UniqueConstraint(
            "kaq_assessment_id",
            "kaq_position",
            name="uq_knowledge_assessment_question_position",
        ),
        UniqueConstraint(
            "kaq_id",
            "kaq_assessment_id",
            name="uq_knowledge_assessment_question_assessment",
        ),
        CheckConstraint(
            "kaq_position BETWEEN 1 AND 5",
            name="ck_knowledge_assessment_question_position",
        ),
        CheckConstraint(
            "length(btrim(kaq_statement)) > 0",
            name="ck_knowledge_assessment_question_statement",
        ),
    )

    kaq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kaq_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_assessment.kas_id", ondelete="CASCADE"),
        nullable=False,
    )
    kaq_statement: Mapped[str] = mapped_column(Text, nullable=False)
    kaq_position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    assessment: Mapped["KnowledgeAssessment"] = relationship(
        back_populates="questions"
    )
    alternatives: Mapped[
        list["KnowledgeAssessmentAlternative"]
    ] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="KnowledgeAssessmentAlternative.kaa_position.asc()",
    )
    answers: Mapped[list["KnowledgeAssessmentAnswer"]] = relationship(
        back_populates="question",
        foreign_keys="KnowledgeAssessmentAnswer.kar_question_id",
    )
