from importlib.metadata import version

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    GROQ_PROMPT_VERSION: str = "v1"
    AI_MEMORY_ENABLED: bool = True
    AI_MEMORY_FINGERPRINT_VERSION: str = "v1"
    AI_MEMORY_LEASE_SECONDS: int = 120
    AI_MEMORY_REDIS_LOCK_ENABLED: bool = True


Env = _Env()
