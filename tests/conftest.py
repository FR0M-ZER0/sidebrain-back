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
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum
from sidebrain_back.models import Answer, Lesson, Quiz, Step, Track, User


@dataclass
class LearningHierarchy:
    user: User
    track: Track
    step: Step
    lesson: Lesson


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
        await db_session.flush()
        return answer

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
