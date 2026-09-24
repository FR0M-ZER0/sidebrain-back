from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAcceptedResponse,
    AssessmentAnswersRequest,
    AssessmentCreateRequest,
    AssessmentDetail,
)
from sidebrain_back.services.knowledge_assessment_service import (
    KnowledgeAssessmentService,
    get_knowledge_assessment_service,
)

router = APIRouter(prefix="/v1/assessments", tags=["Assessments"])


@router.post(
    "",
    response_model=AssessmentAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_knowledge_assessment(
    payload: AssessmentCreateRequest,
    response: Response,
    user: User = Depends(get_current_user),  # noqa: B008
    service: KnowledgeAssessmentService = Depends(  # noqa: B008
        get_knowledge_assessment_service
    ),
) -> AssessmentAcceptedResponse:
    result = await service.create_knowledge_assessment(user, payload)
    response.headers["Location"] = (
        f"/api/v1/assessments/{result.assessment_id}"
    )
    if result.status is KnowledgeAssessmentStatusEnum.GENERATED:
        response.status_code = status.HTTP_200_OK
    return result


@router.get("/{assessment_id}", response_model=AssessmentDetail)
async def get_knowledge_assessment(
    assessment_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: KnowledgeAssessmentService = Depends(  # noqa: B008
        get_knowledge_assessment_service
    ),
) -> AssessmentDetail:
    return await service.get_knowledge_assessment(user, assessment_id)


@router.post("/{assessment_id}/answers", response_model=AssessmentDetail)
async def submit_knowledge_assessment_answers(
    assessment_id: UUID,
    payload: AssessmentAnswersRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: KnowledgeAssessmentService = Depends(  # noqa: B008
        get_knowledge_assessment_service
    ),
) -> AssessmentDetail:
    return await service.submit_knowledge_assessment_answers(
        user, assessment_id, payload
    )
