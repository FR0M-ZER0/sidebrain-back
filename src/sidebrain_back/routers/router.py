from fastapi import APIRouter

from sidebrain_back.routers.v1.auth_router import router as auth_router
from sidebrain_back.routers.v1.avatar_router import router as avatar_router
from sidebrain_back.routers.v1.badge_router import router as badge_router
from sidebrain_back.routers.v1.feedback_router import router as feedback_router
from sidebrain_back.routers.v1.health_router import router as health_router
from sidebrain_back.routers.v1.job_update_router import (
    router as job_update_router,
)
from sidebrain_back.routers.v1.knowledge_assessment_router import (
    router as knowledge_assessment_router,
)
from sidebrain_back.routers.v1.lesson_router import router as lesson_router
from sidebrain_back.routers.v1.mentor_consent_router import (
    router as mentor_consent_router,
)
from sidebrain_back.routers.v1.mentor_router import router as mentor_router
from sidebrain_back.routers.v1.mission_router import router as mission_router
from sidebrain_back.routers.v1.notification_router import (
    router as notification_router,
)
from sidebrain_back.routers.v1.quiz_router import router as quiz_router
from sidebrain_back.routers.v1.ranking_router import router as ranking_router
from sidebrain_back.routers.v1.step_router import router as step_router
from sidebrain_back.routers.v1.track_router import router as track_router
from sidebrain_back.routers.v1.user_router import router as user_router
from sidebrain_back.routers.v1.user_statistics_router import (
    router as user_statistics_router,
)

router = APIRouter(prefix="/api")

router.include_router(auth_router)
router.include_router(avatar_router)
router.include_router(feedback_router)
router.include_router(badge_router)
router.include_router(health_router)
router.include_router(lesson_router)
router.include_router(job_update_router)
router.include_router(mentor_consent_router)
router.include_router(mentor_router)
router.include_router(mission_router)
router.include_router(notification_router)
router.include_router(knowledge_assessment_router)
router.include_router(quiz_router)
router.include_router(ranking_router)
router.include_router(step_router)
router.include_router(track_router)
router.include_router(user_statistics_router)
router.include_router(user_router)
