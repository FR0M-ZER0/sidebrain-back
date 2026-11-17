import pytest

from sidebrain_back.core import llm_client


@pytest.fixture(autouse=True)
def clear_client_cache():
    llm_client.get_llm_client.cache_clear()
    yield
    llm_client.get_llm_client.cache_clear()


def test_chat_uses_openai_when_dedicated_key_is_configured(monkeypatch):
    monkeypatch.setattr(llm_client.Env, "OPENAI_CHAT_API_KEY", "openai-key")
    monkeypatch.setattr(llm_client.Env, "OPENAI_CHAT_MODEL", "openai-model")
    monkeypatch.setattr(llm_client.Env, "OPENAI_API_KEY", "embedding-key")
    monkeypatch.setattr(llm_client.Env, "GROQ_API_KEY", "groq-key")
    created_clients = []

    def fake_openai(**kwargs):
        created_clients.append(kwargs)
        return kwargs

    monkeypatch.setattr(llm_client, "OpenAI", fake_openai)

    client = llm_client.get_llm_client()

    assert client == {"api_key": "openai-key"}
    assert created_clients == [{"api_key": "openai-key"}]
    assert llm_client.get_llm_model() == "openai-model"


def test_chat_uses_groq_when_openai_chat_key_is_missing(monkeypatch):
    monkeypatch.setattr(llm_client.Env, "OPENAI_CHAT_API_KEY", None)
    monkeypatch.setattr(llm_client.Env, "OPENAI_API_KEY", "embedding-key")
    monkeypatch.setattr(llm_client.Env, "GROQ_API_KEY", "groq-key")
    monkeypatch.setattr(llm_client.Env, "GROQ_CHAT_MODEL", "llama-model")
    monkeypatch.setattr(llm_client.Env, "GROQ_MODEL", "legacy-model")
    created_clients = []

    def fake_openai(**kwargs):
        created_clients.append(kwargs)
        return kwargs

    monkeypatch.setattr(llm_client, "OpenAI", fake_openai)

    client = llm_client.get_llm_client()

    assert client == {
        "api_key": "groq-key",
        "base_url": llm_client.GROQ_BASE_URL,
    }
    assert created_clients == [client]
    assert llm_client.get_llm_model() == "llama-model"


def test_chat_uses_legacy_groq_model_when_new_setting_is_missing(monkeypatch):
    monkeypatch.setattr(llm_client.Env, "OPENAI_CHAT_API_KEY", None)
    monkeypatch.setattr(llm_client.Env, "GROQ_CHAT_MODEL", None)
    monkeypatch.setattr(llm_client.Env, "GROQ_MODEL", "legacy-model")

    assert llm_client.get_llm_model() == "legacy-model"


def test_chat_uses_supported_default_groq_model_when_unconfigured(monkeypatch):
    monkeypatch.setattr(llm_client.Env, "OPENAI_CHAT_API_KEY", None)
    monkeypatch.setattr(llm_client.Env, "GROQ_CHAT_MODEL", None)
    monkeypatch.setattr(llm_client.Env, "GROQ_MODEL", None)

    assert llm_client.get_llm_model() == "openai/gpt-oss-120b"


def test_chat_rejects_missing_credentials_when_groq_is_selected(monkeypatch):
    monkeypatch.setattr(llm_client.Env, "OPENAI_CHAT_API_KEY", "  ")
    monkeypatch.setattr(llm_client.Env, "GROQ_API_KEY", None)

    with pytest.raises(llm_client.LLMConfigurationError, match="GROQ_API_KEY"):
        llm_client.get_llm_client()
