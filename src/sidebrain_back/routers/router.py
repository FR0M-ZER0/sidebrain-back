from fastapi import APIRouter

from sidebrain_back.routers.v1.health_router import router as health_router
from sidebrain_back.routers.v1.track_router import router as track_router

router = APIRouter(prefix="/api")

router.include_router(health_router)
router.include_router(track_router)
