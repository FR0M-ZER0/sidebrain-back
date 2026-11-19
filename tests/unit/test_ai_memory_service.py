import pytest

from sidebrain_back.core.constants import Env
from sidebrain_back.services.ai_memory_service import AIMemoryService


def test_canonicalize_text_removes_accents_case_and_peripheral_punctuation():
    assert AIMemoryService.canonicalize_text("  ¡INGLÊS!  ") == "ingles"


def test_canonicalize_text_rejects_empty_values():
    with pytest.raises(ValueError):
        AIMemoryService.canonicalize_text(" ... ")


def test_fingerprint_is_deterministic_and_versioned():
    first, first_envelope = AIMemoryService.fingerprint(
        content_type="track",
        canonical_context={"topic": "Python", "goal": "Fundamentos"},
        model="model-a",
        prompt_version="prompt-a",
    )
    second, second_envelope = AIMemoryService.fingerprint(
        content_type="track",
        canonical_context={"goal": "fundamentos", "topic": "python"},
        model="model-a",
        prompt_version="prompt-a",
    )

    assert first == second
    assert first_envelope == second_envelope


def test_fingerprint_changes_when_model_or_prompt_changes():
    base = {
        "content_type": "assessment",
        "canonical_context": {"subject": "python"},
        "model": "model-a",
        "prompt_version": "prompt-a",
    }
    model_fingerprint, _ = AIMemoryService.fingerprint(
        **{**base, "model": "model-b"}
    )
    prompt_fingerprint, _ = AIMemoryService.fingerprint(
        **{**base, "prompt_version": "prompt-b"}
    )
    original, _ = AIMemoryService.fingerprint(**base)

    assert original != model_fingerprint
    assert original != prompt_fingerprint


def test_fingerprint_uses_selected_provider_and_model(monkeypatch):
    monkeypatch.setattr(Env, "OPENAI_CHAT_API_KEY", "key")
    monkeypatch.setattr(Env, "OPENAI_CHAT_MODEL", "shared-model")
    monkeypatch.setattr(Env, "GROQ_CHAT_MODEL", "shared-model")
    openai_key, envelope = AIMemoryService.fingerprint(
        content_type="assessment", canonical_context={"subject": "python"}
    )
    monkeypatch.setattr(Env, "OPENAI_CHAT_API_KEY", None)
    groq_key, groq_envelope = AIMemoryService.fingerprint(
        content_type="assessment", canonical_context={"subject": "python"}
    )
    assert envelope["provider"] == "openai"
    assert groq_envelope["provider"] == "groq"
    assert envelope["model"] == groq_envelope["model"] == "shared-model"
    assert openai_key != groq_key
