from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.models.answer_model import Answer
from sidebrain_back.models.generation_request_model import GenerationRequest
from sidebrain_back.models.knowledge_assessment_model import (
    KnowledgeAssessment,
)
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track


class MentorContextRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: UUID, track_id: UUID) -> dict | None:
        track = await self.db.scalar(
            select(Track).where(
                Track.trk_id == track_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
        )
        if track is None:
            return None
        steps = (
            await self.db.execute(
                select(Step.stp_title, Step.stp_status, Step.stp_updated_at)
                .where(
                    Step.stp_track_id == track_id,
                    Step.stp_is_deleted.is_(False),
                )
                .order_by(Step.stp_updated_at.desc(), Step.stp_id.desc())
                .limit(20)
            )
        ).all()
        total, completed = (
            await self.db.execute(
                select(
                    func.count(Lesson.lsn_id),
                    func.count(Lesson.lsn_id).filter(
                        Lesson.lsn_status == LessonStatusEnum.DONE
                    ),
                )
                .join(Step, Step.stp_id == Lesson.lsn_step_id)
                .where(
                    Step.stp_track_id == track_id,
                    Step.stp_is_deleted.is_(False),
                    Lesson.lsn_is_deleted.is_(False),
                )
            )
        ).one()
        answers = (
            await self.db.execute(
                select(
                    Answer.ans_rate, Answer.ans_reason, Answer.ans_created_at
                )
                .join(Quiz, Quiz.qui_id == Answer.ans_question_id)
                .join(Lesson, Lesson.lsn_id == Quiz.qui_lesson_id)
                .join(Step, Step.stp_id == Lesson.lsn_step_id)
                .join(Track, Track.trk_id == Step.stp_track_id)
                .where(
                    Track.trk_id == track_id,
                    Track.trk_user_id == user_id,
                    Track.trk_is_deleted.is_(False),
                    Step.stp_is_deleted.is_(False),
                    Lesson.lsn_is_deleted.is_(False),
                    Quiz.qui_is_deleted.is_(False),
                    Answer.ans_user_id == user_id,
                )
                .order_by(Answer.ans_created_at.desc(), Answer.ans_id.desc())
                .limit(20)
            )
        ).all()
        assessment = (
            await self.db.execute(
                select(
                    KnowledgeAssessment.kas_status,
                    KnowledgeAssessment.kas_score,
                    KnowledgeAssessment.kas_level,
                    KnowledgeAssessment.kas_completed_at,
                )
                .join(
                    GenerationRequest,
                    GenerationRequest.assessment_id
                    == KnowledgeAssessment.kas_id,
                )
                .where(
                    GenerationRequest.request_id
                    == track.trk_generation_request_id,
                    GenerationRequest.user_id == user_id,
                    KnowledgeAssessment.kas_user_id == user_id,
                )
            )
        ).one_or_none()
        result = {
            "trilha": track.trk_title,
            "descricao_trilha": (track.trk_description or "")[:1000],
            "etapas": [
                {
                    "titulo": row.stp_title,
                    "estado": row.stp_status.value,
                    "atualizado_em": row.stp_updated_at.isoformat(),
                }
                for row in steps
            ],
            "progresso": {"aulas": total, "concluidas": completed},
            "respostas_recentes": [
                {
                    "classificacao": row.ans_rate.value,
                    "justificativa": (row.ans_reason or "")[:600],
                    "data": row.ans_created_at.isoformat(),
                }
                for row in answers
            ],
        }
        if assessment is not None:
            assessment_status = assessment.kas_status.value
            result["avaliacao_inicial"] = {
                "estado": assessment_status,
                "pontuacao": assessment.kas_score,
                "nivel": (
                    assessment.kas_level.value
                    if assessment_status == "completed"
                    and assessment.kas_level is not None
                    else None
                ),
                "data": (
                    assessment.kas_completed_at.isoformat()
                    if assessment.kas_completed_at is not None
                    else None
                ),
            }
        return result


def get_mentor_context_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MentorContextRepository:
    return MentorContextRepository(db)
