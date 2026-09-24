from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from sidebrain_back.core.auth import get_current_user
from sidebrain_back.core.database import Base, engine, get_db
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.enums.lesson_file_type_enum import LessonFileTypeEnum
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum
from sidebrain_back.models import (
    Answer,
    Feedback,
    KnowledgeAssessment,
    KnowledgeAssessmentAlternative,
    KnowledgeAssessmentAnswer,
    KnowledgeAssessmentQuestion,
    Lesson,
    LessonFile,
    Quiz,
    Step,
    Track,
    User,
)


@dataclass
class LearningHierarchy:
    user: User
    track: Track
    step: Step
    lesson: Lesson


@dataclass
class KnowledgeAssessmentHierarchy:
    owner: User
    other_user: User
    assessment: KnowledgeAssessment
    questions: list[KnowledgeAssessmentQuestion]
    correct_alternatives: list[KnowledgeAssessmentAlternative]
    incorrect_alternatives: list[KnowledgeAssessmentAlternative]


@pytest.fixture
def authenticated_user() -> User:
    return User(
        usr_id=uuid4(),
        usr_email="test@example.com",
        usr_name="Test User",
        usr_password_hash="test-hash",
        usr_is_deleted=False,
    )


@pytest.fixture
def async_session() -> AsyncSession:
    return AsyncSession()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
def learning_hierarchy_factory(db_session: AsyncSession):
    async def create(
        *,
        lesson_status: LessonStatusEnum = LessonStatusEnum.IDLE,
        track_deleted: bool = False,
        step_deleted: bool = False,
        lesson_deleted: bool = False,
    ) -> LearningHierarchy:
        user = User(
            usr_id=uuid4(),
            usr_email=f"{uuid4()}@example.com",
            usr_name="Integration User",
            usr_password_hash="test-hash",
            usr_is_deleted=False,
        )
        track = Track(
            trk_id=uuid4(),
            trk_user_id=user.usr_id,
            trk_title="Python",
            trk_is_deleted=track_deleted,
            trk_deleted_at=(
                datetime.now(UTC).replace(tzinfo=None)
                if track_deleted
                else None
            ),
        )
        step = Step(
            stp_id=uuid4(),
            stp_track_id=track.trk_id,
            stp_level=StepLevelEnum.BEGINNER,
            stp_title="Fundamentos",
            stp_status=StepStatusEnum.IDLE,
            stp_is_deleted=step_deleted,
            stp_deleted_at=(
                datetime.now(UTC).replace(tzinfo=None)
                if step_deleted
                else None
            ),
        )
        lesson = Lesson(
            lsn_id=uuid4(),
            lsn_step_id=step.stp_id,
            lsn_title="Variáveis",
            lsn_text="Conteúdo",
            lsn_status=lesson_status,
            lsn_position=1,
            lsn_is_deleted=lesson_deleted,
            lsn_deleted_at=(
                datetime.now(UTC).replace(tzinfo=None)
                if lesson_deleted
                else None
            ),
        )
        db_session.add_all([user, track, step, lesson])
        await db_session.flush()
        return LearningHierarchy(user, track, step, lesson)

    return create


@pytest.fixture
def quiz_factory(db_session: AsyncSession):
    async def create(
        lesson: Lesson,
        *,
        quiz_id: UUID | None = None,
        question: str = "What is a variable?",
        deleted: bool = False,
        updated_at: datetime | None = None,
        flush: bool = True,
    ) -> Quiz:
        now = updated_at or datetime.now(UTC).replace(tzinfo=None)
        quiz = Quiz(
            qui_id=quiz_id or uuid4(),
            qui_lesson_id=lesson.lsn_id,
            qui_question=question,
            qui_updated_at=now,
            qui_is_deleted=deleted,
            qui_deleted_at=now if deleted else None,
        )
        db_session.add(quiz)
        if flush:
            await db_session.flush()
        return quiz

    return create


@pytest.fixture
def answer_factory(db_session: AsyncSession):
    async def create(
        quiz: Quiz,
        user: User,
        *,
        answer_id: UUID | None = None,
        text: str = "A named reference to a value",
        rate: AnswerRateEnum = AnswerRateEnum.PERFECT,
        created_at: datetime | None = None,
        flush: bool = True,
    ) -> Answer:
        now = created_at or datetime.now(UTC).replace(tzinfo=None)
        answer = Answer(
            ans_id=answer_id or uuid4(),
            ans_question_id=quiz.qui_id,
            ans_user_id=user.usr_id,
            ans_text=text,
            ans_rate=rate,
            ans_created_at=now,
            ans_updated_at=now,
        )
        db_session.add(answer)
        if flush:
            await db_session.flush()
        return answer

    return create


@pytest.fixture
def step_factory(db_session: AsyncSession):
    async def create(
        track: Track,
        *,
        title: str = "Fundamentos",
        deleted: bool = False,
        flush: bool = True,
    ) -> Step:
        now = datetime.now(UTC).replace(tzinfo=None)
        step = Step(
            stp_id=uuid4(),
            stp_track_id=track.trk_id,
            stp_level=StepLevelEnum.BEGINNER,
            stp_title=title,
            stp_status=StepStatusEnum.IDLE,
            stp_is_deleted=deleted,
            stp_deleted_at=now if deleted else None,
        )
        db_session.add(step)
        if flush:
            await db_session.flush()
        return step

    return create


@pytest.fixture
def lesson_factory(db_session: AsyncSession):
    async def create(
        step: Step,
        *,
        title: str = "Variáveis",
        text: str = "Conteúdo",
        status: LessonStatusEnum = LessonStatusEnum.IDLE,
        position: int = 1,
        deleted: bool = False,
        flush: bool = True,
    ) -> Lesson:
        now = datetime.now(UTC).replace(tzinfo=None)
        lesson = Lesson(
            lsn_id=uuid4(),
            lsn_step_id=step.stp_id,
            lsn_title=title,
            lsn_text=text,
            lsn_status=status,
            lsn_position=position,
            lsn_is_deleted=deleted,
            lsn_deleted_at=now if deleted else None,
        )
        db_session.add(lesson)
        if flush:
            await db_session.flush()
        return lesson

    return create


@pytest.fixture
def feedback_factory(db_session: AsyncSession):
    async def create(
        lesson: Lesson,
        user: User,
        *,
        text: str = "Muito útil",
        deleted: bool = False,
        flush: bool = True,
    ) -> Feedback:
        now = datetime.now(UTC).replace(tzinfo=None)
        feedback = Feedback(
            fbk_id=uuid4(),
            fbk_lesson_id=lesson.lsn_id,
            fbk_user_id=user.usr_id,
            fbk_text=text,
            fbk_created_at=now,
            fbk_updated_at=now,
            fbk_is_deleted=deleted,
            fbk_deleted_at=now if deleted else None,
        )
        db_session.add(feedback)
        if flush:
            await db_session.flush()
        return feedback

    return create


@pytest.fixture
def lesson_file_factory(db_session: AsyncSession):
    async def create(
        lesson: Lesson,
        *,
        path: str = "/lessons/content.png",
        file_type: LessonFileTypeEnum = LessonFileTypeEnum.IMAGE,
        deleted: bool = False,
        flush: bool = True,
    ) -> LessonFile:
        now = datetime.now(UTC).replace(tzinfo=None)
        lesson_file = LessonFile(
            lsf_id=uuid4(),
            lsf_lesson_id=lesson.lsn_id,
            lsf_path=path,
            lsf_file_type=file_type,
            lsf_updated_at=now,
            lsf_is_deleted=deleted,
            lsf_deleted_at=now if deleted else None,
        )
        db_session.add(lesson_file)
        if flush:
            await db_session.flush()
        return lesson_file

    return create


@pytest.fixture
def knowledge_assessment_factory(db_session: AsyncSession):
    async def create(
        *,
        owner: User | None = None,
        subject: str = "Python",
        objective: str | None = "Avaliar fundamentos",
        skip: bool = False,
        status: KnowledgeAssessmentStatusEnum = (
            KnowledgeAssessmentStatusEnum.PENDING
        ),
        fingerprint: str | None = None,
        flush: bool = True,
    ) -> KnowledgeAssessment:
        assessment_owner = owner or User(
            usr_id=uuid4(),
            usr_email=f"{uuid4()}@example.com",
            usr_name="Assessment Owner",
            usr_password_hash="test-hash",
            usr_is_deleted=False,
        )
        if owner is None:
            db_session.add(assessment_owner)
        now = datetime.now(UTC).replace(tzinfo=None)
        terminal = {
            KnowledgeAssessmentStatusEnum.SKIPPED,
            KnowledgeAssessmentStatusEnum.COMPLETED,
        }
        assessment = KnowledgeAssessment(
            kas_id=uuid4(),
            kas_user_id=assessment_owner.usr_id,
            kas_subject=subject,
            kas_objective=objective,
            kas_skip=skip,
            kas_context_fingerprint=fingerprint or uuid4().hex * 2,
            kas_status=status,
            kas_score=(
                0
                if status is KnowledgeAssessmentStatusEnum.COMPLETED
                else None
            ),
            kas_level=(
                StepLevelEnum.BEGINNER if status in terminal else None
            ),
            kas_error_code=(
                "generation_failed"
                if status is KnowledgeAssessmentStatusEnum.FAILED
                else None
            ),
            kas_completed_at=now if status in terminal else None,
        )
        db_session.add(assessment)
        if flush:
            await db_session.flush()
        return assessment

    return create


@pytest.fixture
def knowledge_question_factory(db_session: AsyncSession):
    async def create(
        assessment: KnowledgeAssessment,
        *,
        position: int = 1,
        statement: str | None = None,
        flush: bool = True,
    ) -> KnowledgeAssessmentQuestion:
        question = KnowledgeAssessmentQuestion(
            kaq_id=uuid4(),
            kaq_assessment_id=assessment.kas_id,
            kaq_statement=statement or f"Pergunta {position}?",
            kaq_position=position,
        )
        db_session.add(question)
        if flush:
            await db_session.flush()
        return question

    return create


@pytest.fixture
def knowledge_alternative_factory(db_session: AsyncSession):
    async def create(
        question: KnowledgeAssessmentQuestion,
        *,
        position: int = 1,
        text: str | None = None,
        is_correct: bool = False,
        flush: bool = True,
    ) -> KnowledgeAssessmentAlternative:
        alternative = KnowledgeAssessmentAlternative(
            kaa_id=uuid4(),
            kaa_question_id=question.kaq_id,
            kaa_text=text or f"Alternativa {position}",
            kaa_position=position,
            kaa_is_correct=is_correct,
        )
        db_session.add(alternative)
        if flush:
            await db_session.flush()
        return alternative

    return create


@pytest.fixture
def knowledge_answer_factory(db_session: AsyncSession):
    async def create(
        assessment: KnowledgeAssessment,
        question: KnowledgeAssessmentQuestion,
        alternative: KnowledgeAssessmentAlternative,
        *,
        flush: bool = True,
    ) -> KnowledgeAssessmentAnswer:
        answer = KnowledgeAssessmentAnswer(
            kar_id=uuid4(),
            kar_assessment_id=assessment.kas_id,
            kar_question_id=question.kaq_id,
            kar_alternative_id=alternative.kaa_id,
        )
        db_session.add(answer)
        if flush:
            await db_session.flush()
        return answer

    return create


@pytest.fixture
def knowledge_assessment_hierarchy_factory(
    db_session: AsyncSession,
    knowledge_assessment_factory,
    knowledge_question_factory,
    knowledge_alternative_factory,
):
    async def create() -> KnowledgeAssessmentHierarchy:
        owner = User(
            usr_id=uuid4(),
            usr_email=f"{uuid4()}@example.com",
            usr_name="Assessment Owner",
            usr_password_hash="test-hash",
            usr_is_deleted=False,
        )
        other_user = User(
            usr_id=uuid4(),
            usr_email=f"{uuid4()}@example.com",
            usr_name="Other User",
            usr_password_hash="test-hash",
            usr_is_deleted=False,
        )
        db_session.add_all([owner, other_user])
        await db_session.flush()
        assessment = await knowledge_assessment_factory(
            owner=owner,
            status=KnowledgeAssessmentStatusEnum.GENERATED,
        )
        questions = []
        correct_alternatives = []
        incorrect_alternatives = []
        for question_position in range(1, 6):
            question = await knowledge_question_factory(
                assessment,
                position=question_position,
            )
            questions.append(question)
            for alternative_position in range(1, 5):
                alternative = await knowledge_alternative_factory(
                    question,
                    position=alternative_position,
                    is_correct=alternative_position == 1,
                )
                if alternative.kaa_is_correct:
                    correct_alternatives.append(alternative)
                else:
                    incorrect_alternatives.append(alternative)
        return KnowledgeAssessmentHierarchy(
            owner=owner,
            other_user=other_user,
            assessment=assessment,
            questions=questions,
            correct_alternatives=correct_alternatives,
            incorrect_alternatives=incorrect_alternatives,
        )

    return create


@pytest.fixture
def dependency_overrides(
    async_session: AsyncSession, authenticated_user: User
) -> dict:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield async_session

    async def override_current_user() -> User:
        return authenticated_user

    return {
        get_db: override_get_db,
        get_current_user: override_current_user,
    }


@pytest.fixture
def test_app(dependency_overrides: dict) -> FastAPI:
    app.dependency_overrides.update(dependency_overrides)
    yield app
    app.dependency_overrides.clear()
