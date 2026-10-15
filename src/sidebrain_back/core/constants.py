from importlib.metadata import version
from typing import Literal

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
    REDIS_AUTH_DB: Literal[2] = 2

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: Literal[60] = 60

    GROQ_API_KEY: str
    GROQ_MODEL: str


Env = _Env()
