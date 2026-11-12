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

    TEST_POSTGRES_HOST: str | None = None
    TEST_POSTGRES_PORT: int | None = None
    TEST_POSTGRES_USER: str | None = None
    TEST_POSTGRES_PASSWORD: str | None = None
    TEST_POSTGRES_DB: str | None = None

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_AUTH_DB: Annotated[Literal[2], BeforeValidator(int)] = 2

    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_EXCHANGE: str = "notification.exchange"
    RABBITMQ_ROUTING_KEY: str = "notification"
    RABBITMQ_QUEUE: str = "notification.queue"
    RABBITMQ_DLX: str = "notification.dlx"
    RABBITMQ_DLQ: str = "notification.dead-letter.queue"
    RABBITMQ_MAX_ATTEMPTS: int = 5
    RABBITMQ_RETRY_DELAY_SECONDS: float = 1.0
    RABBITMQ_BACKOFF_FACTOR: float = 2.0

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: Annotated[
        Literal[10080], BeforeValidator(int)
    ] = 10080

    GROQ_API_KEY: str | None = None
    GROQ_CHAT_MODEL: str | None = None
    # Mantido para que arquivos .env antigos continuem sendo carregados.
    GROQ_MODEL: str | None = None
    OPENAI_CHAT_API_KEY: str | None = None
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

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

    @field_validator(
        "RABBITMQ_HOST",
        "RABBITMQ_USER",
        "RABBITMQ_PASSWORD",
        "RABBITMQ_VHOST",
        "RABBITMQ_EXCHANGE",
        "RABBITMQ_ROUTING_KEY",
        "RABBITMQ_QUEUE",
        "RABBITMQ_DLX",
        "RABBITMQ_DLQ",
    )
    @classmethod
    def validate_rabbitmq_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("configuração RabbitMQ não pode ser vazia")
        return value

    @field_validator("RABBITMQ_PORT")
    @classmethod
    def validate_rabbitmq_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("RABBITMQ_PORT deve estar entre 1 e 65535")
        return value

    @field_validator("RABBITMQ_MAX_ATTEMPTS")
    @classmethod
    def validate_rabbitmq_attempts(cls, value: int) -> int:
        if value < 1:
            raise ValueError("RABBITMQ_MAX_ATTEMPTS deve ser positivo")
        return value

    @field_validator(
        "RABBITMQ_RETRY_DELAY_SECONDS",
        "RABBITMQ_BACKOFF_FACTOR",
    )
    @classmethod
    def validate_rabbitmq_backoff(cls, value: float) -> float:
        if value < 0:
            raise ValueError("parâmetros de backoff não podem ser negativos")
        return value

    OPENAI_API_KEY: str | None = None
    RAG_ROUTER_CONFIDENCE_THRESHOLD: float = 0.80
    RAG_SOURCES_CONFIG: str = "config/rag_sources.yml"

    STEP_SUMMARY_MODEL_PATH: str = "artifacts/step_summary_classifier.joblib"


Env = _Env()
