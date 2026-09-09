from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from sidebrain_back.core.constants import Env

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{Env.POSTGRES_USER}:{Env.POSTGRES_PASSWORD}"
    f"@{Env.POSTGRES_HOST}:{Env.POSTGRES_PORT}"
    f"/{Env.POSTGRES_DB}"
)

engine = create_async_engine(DATABASE_URL, echo=Env.MODE == "dev")

async_session = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db():
    async with async_session() as session:
        yield session


# Classe base para a criação de todos os models do projeto
class Base(DeclarativeBase):
    pass
