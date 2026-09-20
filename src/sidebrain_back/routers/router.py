from fastapi import APIRouter

from sidebrain_back.routers.v1.feedback_router import router as feedback_router
from sidebrain_back.routers.v1.health_router import router as health_router
from sidebrain_back.routers.v1.quiz_router import router as quiz_router
from sidebrain_back.routers.v1.track_router import router as track_router

router = APIRouter(prefix="/api")

router.include_router(feedback_router)
router.include_router(health_router)
router.include_router(quiz_router)
router.include_router(track_router)
