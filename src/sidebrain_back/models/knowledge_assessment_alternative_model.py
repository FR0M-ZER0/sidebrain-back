import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.knowledge_assessment_answer_model import (
        KnowledgeAssessmentAnswer,
    )
    from sidebrain_back.models.knowledge_assessment_question_model import (
        KnowledgeAssessmentQuestion,
    )


class KnowledgeAssessmentAlternative(Base):
    __tablename__ = "knowledge_assessment_alternative"
    __table_args__ = (
        UniqueConstraint(
            "kaa_question_id",
            "kaa_position",
            name="uq_knowledge_assessment_alternative_position",
        ),
        UniqueConstraint(
            "kaa_id",
            "kaa_question_id",
            name="uq_knowledge_assessment_alternative_question",
        ),
        CheckConstraint(
            "kaa_position BETWEEN 1 AND 4",
            name="ck_knowledge_assessment_alternative_position",
        ),
        CheckConstraint(
            "length(btrim(kaa_text)) > 0",
            name="ck_knowledge_assessment_alternative_text",
        ),
        Index(
            "uq_knowledge_assessment_alternative_correct",
            "kaa_question_id",
            unique=True,
            postgresql_where=text("kaa_is_correct IS true"),
        ),
    )

    kaa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kaa_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "knowledge_assessment_question.kaq_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    kaa_text: Mapped[str] = mapped_column(Text, nullable=False)
    kaa_position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    kaa_is_correct: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    question: Mapped["KnowledgeAssessmentQuestion"] = relationship(
        back_populates="alternatives"
    )
    answers: Mapped[list["KnowledgeAssessmentAnswer"]] = relationship(
        back_populates="alternative",
        foreign_keys="KnowledgeAssessmentAnswer.kar_alternative_id",
    )
