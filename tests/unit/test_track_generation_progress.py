from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.generation_status_enum import GenerationStatusEnum
from sidebrain_back.services.track_service import TrackService


class FakeGenerationRequests:
    def __init__(self, request):
        self.request = request
        self.request_id = None
        self.user_id = None

    async def get_by_request_and_user(self, request_id, user_id):
        self.request_id = request_id
        self.user_id = user_id
        return self.request


class FakeSession:
    async def rollback(self):
        pass


@pytest.mark.anyio
async def test_get_generation_progress_returns_owned_request_state():
    user_id = uuid4()
    request_id = uuid4()
    track_id = uuid4()
    requests = FakeGenerationRequests(
        SimpleNamespace(
            request_id=request_id,
            status=GenerationStatusEnum.SUCCEEDED,
            track_id=track_id,
            error_code=None,
        )
    )
    service = TrackService(None, FakeSession(), requests)

    progress = await service.get_generation_progress(user_id, request_id)

    assert progress.model_dump() == {
        "request_id": request_id,
        "status": GenerationStatusEnum.SUCCEEDED,
        "track_id": track_id,
        "error_code": None,
    }
    assert requests.request_id == request_id
    assert requests.user_id == user_id


@pytest.mark.anyio
async def test_get_generation_progress_hides_missing_or_unowned_request():
    service = TrackService(None, FakeSession(), FakeGenerationRequests(None))

    with pytest.raises(ProblemDetailError) as error:
        await service.get_generation_progress(uuid4(), uuid4())

    assert error.value.status_code == 404
