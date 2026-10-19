from importlib.metadata import version

from pydantic_settings import BaseSettings, SettingsConfigDict

RAG_VECTOR_DIMENSIONS = 1536


class _Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    HOST: str
    PORT: int
    MODE: str
    VERSION: str = version("sidebrain_back")

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    REDIS_HOST: str
    REDIS_PORT: int

    GROQ_API_KEY: str
    GROQ_MODEL: str

    OPENAI_API_KEY: str | None = None
    RAG_ROUTER_CONFIDENCE_THRESHOLD: float = 0.80
    RAG_SOURCES_CONFIG: str = "config/rag_sources.yml"


Env = _Env()
