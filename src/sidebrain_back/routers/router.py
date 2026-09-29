from fastapi import APIRouter

from sidebrain_back.routers.v1.feedback_router import router as feedback_router
from sidebrain_back.routers.v1.health_router import router as health_router
from sidebrain_back.routers.v1.knowledge_assessment_router import (
    router as knowledge_assessment_router,
)
from sidebrain_back.routers.v1.lesson_router import router as lesson_router
from sidebrain_back.routers.v1.quiz_router import router as quiz_router
from sidebrain_back.routers.v1.step_router import router as step_router
from sidebrain_back.routers.v1.track_router import router as track_router

router = APIRouter(prefix="/api")

router.include_router(feedback_router)
router.include_router(health_router)
router.include_router(lesson_router)
router.include_router(knowledge_assessment_router)
router.include_router(quiz_router)
router.include_router(step_router)
router.include_router(track_router)
