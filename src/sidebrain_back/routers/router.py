from fastapi import APIRouter

from sidebrain_back.routers.v1.health_router import router as health_router

router = APIRouter(prefix="/api")

router.include_router(health_router)
