from fastapi import FastAPI
from uvicorn import run

from sidebrain_back.core.constants import Env
from sidebrain_back.routers.router import router as api_router


def create_app() -> FastAPI:
    application = FastAPI(title="Sidebrain API", version=Env.VERSION)

    application.include_router(api_router)

    return application


app = create_app()


def main():
    run(
        "sidebrain_back.main:app",
        host=Env.HOST,
        port=Env.PORT,
        reload=Env.MODE == "dev",
    )


if __name__ == "__main__":
    main()
