from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn import run

from sidebrain_back.core.constants import Env
from sidebrain_back.core.cors import configure_cors
from sidebrain_back.core.errors import register_error_handlers
from sidebrain_back.core.job_notifications import (
    close_job_notification_listener,
    start_job_notification_listener,
)
from sidebrain_back.core.logging import configure_access_log_redaction
from sidebrain_back.core.rate_limit import close_rate_limit_client
from sidebrain_back.core.ws_tickets import close_ws_ticket_client
from sidebrain_back.routers.router import router as api_router


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    await start_job_notification_listener()
    try:
        yield
    finally:
        await close_job_notification_listener()
        await close_ws_ticket_client()
        await close_rate_limit_client()


def create_app() -> FastAPI:
    configure_access_log_redaction()
    application = FastAPI(
        title="Sidebrain API",
        version=Env.VERSION,
        lifespan=lifespan,
    )
    configure_cors(application)
    register_error_handlers(application)

    static_dir = Path(__file__).resolve().parent / "sidebrain_back" / "static"
    application.mount(
        "/static", StaticFiles(directory=static_dir), name="static"
    )
    application.include_router(api_router)

    return application


app = create_app()


def main():
    run(
        "main:app",
        host=Env.HOST,
        port=Env.PORT,
        reload=Env.MODE == "dev",
    )


if __name__ == "__main__":
    main()
