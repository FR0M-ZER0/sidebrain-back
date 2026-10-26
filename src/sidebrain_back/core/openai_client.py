from functools import lru_cache

from openai import OpenAI

from sidebrain_back.core.constants import Env


@lru_cache
def get_openai_client() -> OpenAI:
    return OpenAI(
        api_key=Env.GROQ_API_KEY,
    )
