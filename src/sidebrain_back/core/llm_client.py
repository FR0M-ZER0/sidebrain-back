from functools import lru_cache

from openai import OpenAI

from sidebrain_back.core.constants import Env

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_CHAT_MODEL = "openai/gpt-oss-120b"


class LLMConfigurationError(ValueError):
    """Raised when no chat provider credentials are configured."""


def _openai_chat_api_key() -> str | None:
    api_key = Env.OPENAI_CHAT_API_KEY
    if api_key is None or not api_key.strip():
        return None
    return api_key.strip()


@lru_cache
def get_llm_client() -> OpenAI:
    openai_api_key = _openai_chat_api_key()
    if openai_api_key is not None:
        return OpenAI(api_key=openai_api_key)

    groq_api_key = Env.GROQ_API_KEY
    if groq_api_key is None or not groq_api_key.strip():
        raise LLMConfigurationError(
            "GROQ_API_KEY is required when OPENAI_CHAT_API_KEY is not set"
        )

    return OpenAI(
        api_key=groq_api_key.strip(),
        base_url=GROQ_BASE_URL,
    )


def get_llm_model() -> str:
    if _openai_chat_api_key() is not None:
        return Env.OPENAI_CHAT_MODEL
    return Env.GROQ_CHAT_MODEL or Env.GROQ_MODEL or DEFAULT_GROQ_CHAT_MODEL
