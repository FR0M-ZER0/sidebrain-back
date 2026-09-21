from uuid import uuid4

from sidebrain_back.schemas.generation_schema import (
    AssessmentAnswer,
    GenerationInput,
)
from sidebrain_back.services.generation_service import GenerationService


def test_generation_prompt_contains_context_and_future_content_boundary():
    payload = GenerationInput(
        request_id=uuid4(),
        user_id=uuid4(),
        goal="Aprender Python",
        topic="Python",
        knowledge_level="beginner",
        assessment_answers=[
            AssessmentAnswer(
                question="Já programou?", answer="Não", rate="wrong"
            )
        ],
    )

    prompt = GenerationService.build_prompt(payload)

    assert "Aprender Python" in prompt
    assert "beginner" in prompt
    assert "somente para a etapa de posição 1" in prompt
    future_instruction = (
        "etapas posteriores devem conter apenas posição, nível e título"
    )
    assert future_instruction in prompt
    assert str(payload.request_id) not in prompt
    assert str(payload.user_id) not in prompt
