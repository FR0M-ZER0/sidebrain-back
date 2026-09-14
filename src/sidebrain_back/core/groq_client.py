from functools import lru_cache

from groq import Groq

from sidebrain_back.core.constants import Env


@lru_cache
def get_groq_client() -> Groq:
    return Groq(
        api_key=Env.GROQ_API_KEY,
    )
