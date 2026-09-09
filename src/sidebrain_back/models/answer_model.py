import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum

if TYPE_CHECKING:
    from sidebrain_back.models.quiz_model import Quiz
    from sidebrain_back.models.user_model import User


class Answer(Base):
    __tablename__ = "answer"

    ans_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    ans_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quiz.qui_id", ondelete="CASCADE"),
        nullable=False,
    )
    ans_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
    )
    ans_text: Mapped[str] = mapped_column(Text, nullable=False)
    ans_rate: Mapped[AnswerRateEnum] = mapped_column(
        ENUM(
            AnswerRateEnum,
            name="answer_rate",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    ans_created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    ans_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    quiz: Mapped["Quiz"] = relationship(back_populates="answers")
    user: Mapped["User"] = relationship(back_populates="answers")

    def __repr__(self) -> str:
        return f"<Answer ans_id={self.ans_id} ans_rate={self.ans_rate}>"
