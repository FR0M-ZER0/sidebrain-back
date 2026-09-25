from importlib.metadata import version

from pydantic_settings import BaseSettings, SettingsConfigDict


class _Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    HOST: str
    PORT: int
    MODE: str
    VERSION: str = version("sidebrain_back")

    DATABASE_URL: str | None = None

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    REDIS_HOST: str
    REDIS_PORT: int

    GROQ_API_KEY: str
    GROQ_MODEL: str


Env = _Env()
