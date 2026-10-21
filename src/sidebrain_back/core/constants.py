from importlib.metadata import version
from typing import Annotated, Literal

from pydantic import BeforeValidator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MIN_JWT_SECRET_BYTES = 32
_MIN_JWT_SECRET_UNIQUE_CHARACTERS = 12
_JWT_PLACEHOLDER_PREFIXES = ("replace", "substitua", "troque")
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
    REDIS_AUTH_DB: Annotated[Literal[2], BeforeValidator(int)] = 2

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: Annotated[
        Literal[60], BeforeValidator(int)
    ] = 60

    GROQ_API_KEY: str
    GROQ_MODEL: str

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        normalized = value.strip()
        is_placeholder = normalized.lower().startswith(
            _JWT_PLACEHOLDER_PREFIXES
        )
        if (
            normalized != value
            or len(value.encode("utf-8")) < _MIN_JWT_SECRET_BYTES
            or len(set(value)) < _MIN_JWT_SECRET_UNIQUE_CHARACTERS
            or is_placeholder
        ):
            raise ValueError(
                "JWT_SECRET_KEY deve ter ao menos 32 bytes, diversidade "
                "de caracteres e não pode ser um placeholder."
            )
        return value

    OPENAI_API_KEY: str | None = None
    RAG_ROUTER_CONFIDENCE_THRESHOLD: float = 0.80
    RAG_SOURCES_CONFIG: str = "config/rag_sources.yml"


Env = _Env()
