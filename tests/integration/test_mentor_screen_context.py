from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.repositories.mentor_context_repository import (
    MentorContextRepository,
)
from sidebrain_back.repositories.mentor_conversation_repository import (
    MentorConversationRepository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationConflict,
    MentorGenerationRepository,
)
from sidebrain_back.schemas.mentor_schema import MentorMessageCreate
from sidebrain_back.services.mentor_consent_service import MentorConsentService
from sidebrain_back.services.mentor_processing_service import (
    MentorProcessingService,
)
from sidebrain_back.services.mentor_service import (
    MentorNotFound,
    MentorService,
)


async def create_service(db, hierarchy):
    consent_repo = MentorConsentRepository(db)
    consent = MentorConsentService(consent_repo, db)
    service = MentorService(
        MentorConversationRepository(db),
        MentorGenerationRepository(db),
        consent_repo,
        consent,
        db,
        context_repository=MentorContextRepository(db),
    )
    user_id, track_id = hierarchy.user.usr_id, hierarchy.track.trk_id
    conversation = await service.create_mentor_conversation(user_id, track_id)
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    return service, user_id, conversation.id


@pytest.mark.anyio
async def test_screen_context_follows_each_message_and_retry(
    db_session,
    learning_hierarchy_factory,
    lesson_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    lesson_id = hierarchy.lesson.lsn_id
    next_lesson = await lesson_factory(
        hierarchy.step, title="Laços", position=2
    )
    next_lesson_id = next_lesson.lsn_id
    quiz = await quiz_factory(next_lesson, question="O que faz for?")
    answer = await answer_factory(
        quiz,
        hierarchy.user,
        text="Repete o código",
        rate=AnswerRateEnum.ALMOST_GOT_IT,
        reason="Faltou mencionar os itens.",
    )
    quiz_id, answer_id = quiz.qui_id, answer.ans_id
    service, user_id, conversation_id = await create_service(
        db_session, hierarchy
    )
    lesson_context = {"type": "lesson", "lesson_id": str(lesson_id)}
    quiz_context = {
        "type": "quiz",
        "lesson_id": str(next_lesson_id),
        "quiz_id": str(quiz_id),
        "answer_id": str(answer_id),
    }
    key = uuid4()
    lesson_payload = MentorMessageCreate(
        content="Não entendi o for", context=lesson_context
    )
    first = await service.create_mentor_message(
        user_id, conversation_id, key, lesson_payload
    )
    replay = await service.create_mentor_message(
        user_id, conversation_id, key, lesson_payload
    )
    assert replay.generation_id == first.generation_id
    with pytest.raises(MentorGenerationConflict):
        await service.create_mentor_message(
            user_id,
            conversation_id,
            key,
            MentorMessageCreate(
                content=lesson_payload.content, context=quiz_context
            ),
        )
    captured = []

    async def generate(message, _tools, *, history, screen_context):
        captured.append((message, history, screen_context))
        return "Uma dica."

    generator = Mock()
    generator.generate_mentor_response = AsyncMock(side_effect=generate)
    processor = MentorProcessingService(db_session, generator)
    await processor.process(user_id, first.generation_id)
    assert captured[0][2]["tipo"] == "lesson"
    assert captured[0][2]["licao"]["titulo"] == "Variáveis"

    second = await service.create_mentor_message(
        user_id,
        conversation_id,
        uuid4(),
        MentorMessageCreate(
            content="Por que quase certa?", context=quiz_context
        ),
    )
    await processor.process(user_id, second.generation_id)
    screen = captured[1][2]
    assert screen["licao"]["titulo"] == "Laços"
    assert screen["questao"] == "O que faz for?"
    assert screen["avaliacao"] == {
        "resposta": "Repete o código",
        "classificacao": "almost_got_it",
        "justificativa": "Faltou mencionar os itens.",
    }
    assert captured[1][1][0]["content"] == "Não entendi o for"

    failed = await service.create_mentor_message(
        user_id,
        conversation_id,
        uuid4(),
        MentorMessageCreate(content="Explique mais", context=quiz_context),
    )
    failing = Mock()
    failing.generate_mentor_response = AsyncMock(side_effect=ValueError())
    await MentorProcessingService(db_session, failing).process(
        user_id, failed.generation_id
    )
    retried = await service.retry_mentor_generation(
        user_id, conversation_id, failed.generation_id, uuid4()
    )
    await processor.process(user_id, retried.generation_id)
    assert captured[-1][2] == screen


@pytest.mark.anyio
async def test_screen_context_rejects_foreign_or_mismatched_data(
    db_session, learning_hierarchy_factory, quiz_factory, answer_factory
):
    own = await learning_hierarchy_factory()
    foreign = await learning_hierarchy_factory()
    own_quiz = await quiz_factory(own.lesson)
    other_quiz = await quiz_factory(own.lesson, question="Outra pergunta")
    foreign_quiz = await quiz_factory(foreign.lesson)
    foreign_answer = await answer_factory(own_quiz, foreign.user)
    other_answer = await answer_factory(other_quiz, own.user)
    own_lesson_id, foreign_lesson_id = own.lesson.lsn_id, foreign.lesson.lsn_id
    own_quiz_id, foreign_quiz_id = own_quiz.qui_id, foreign_quiz.qui_id
    foreign_answer_id = foreign_answer.ans_id
    other_answer_id = other_answer.ans_id
    service, user_id, conversation_id = await create_service(db_session, own)
    invalid_contexts = [
        {"type": "lesson", "lesson_id": str(foreign_lesson_id)},
        {
            "type": "quiz",
            "lesson_id": str(own_lesson_id),
            "quiz_id": str(foreign_quiz_id),
        },
        {
            "type": "quiz",
            "lesson_id": str(own_lesson_id),
            "quiz_id": str(own_quiz_id),
            "answer_id": str(foreign_answer_id),
        },
        {
            "type": "quiz",
            "lesson_id": str(own_lesson_id),
            "quiz_id": str(own_quiz_id),
            "answer_id": str(other_answer_id),
        },
    ]
    for context in invalid_contexts:
        with pytest.raises(MentorNotFound, match="Contexto indisponível"):
            await service.create_mentor_message(
                user_id,
                conversation_id,
                uuid4(),
                MentorMessageCreate(content="Ajude", context=context),
            )


@pytest.mark.anyio
async def test_question_without_answer_and_legacy_missing_reason(
    db_session, learning_hierarchy_factory, quiz_factory, answer_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    track_id = hierarchy.track.trk_id
    lesson_id = hierarchy.lesson.lsn_id
    quiz = await quiz_factory(hierarchy.lesson, question="Qual é a pergunta?")
    answer = await answer_factory(
        quiz, hierarchy.user, text="Primeira tentativa", reason=None
    )
    await answer_factory(
        quiz, hierarchy.user, text="Segunda tentativa", reason="Outro motivo"
    )
    quiz_id, answer_id = quiz.qui_id, answer.ans_id
    repository = MentorContextRepository(db_session)

    question = await repository.get_screen_context(
        user_id, track_id, lesson_id, quiz_id
    )
    assert question["questao"] == "Qual é a pergunta?"
    assert "avaliacao" not in question
    evaluated = await repository.get_screen_context(
        user_id, track_id, lesson_id, quiz_id, answer_id
    )
    assert evaluated["avaliacao"]["resposta"] == "Primeira tentativa"
    assert evaluated["avaliacao"]["justificativa"] is None


@pytest.mark.anyio
async def test_deleted_question_fails_before_sending_to_provider(
    db_session, learning_hierarchy_factory, quiz_factory
):
    hierarchy = await learning_hierarchy_factory()
    quiz = await quiz_factory(hierarchy.lesson)
    lesson_id, quiz_id = hierarchy.lesson.lsn_id, quiz.qui_id
    service, user_id, conversation_id = await create_service(
        db_session, hierarchy
    )
    submitted = await service.create_mentor_message(
        user_id,
        conversation_id,
        uuid4(),
        MentorMessageCreate(
            content="Ajude",
            context={
                "type": "quiz",
                "lesson_id": str(lesson_id),
                "quiz_id": str(quiz_id),
            },
        ),
    )
    quiz.qui_is_deleted = True
    await db_session.commit()
    generator = Mock()
    generator.generate_mentor_response = AsyncMock()
    await MentorProcessingService(db_session, generator).process(
        user_id, submitted.generation_id
    )
    generator.generate_mentor_response.assert_not_awaited()
    result = await MentorGenerationRepository(db_session).get(
        user_id, conversation_id, submitted.generation_id
    )
    assert result.status == "failed"
