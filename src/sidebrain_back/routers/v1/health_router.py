from datetime import datetime

from fastapi import APIRouter

from sidebrain_back.core.constants import Env

router = APIRouter(prefix="/v1/health", tags=["Health"])


@router.get("/")
async def health_check():
    return {
        "status": "ok",
        "datetime": datetime.now().isoformat(),
        "version": Env.VERSION,
    }
