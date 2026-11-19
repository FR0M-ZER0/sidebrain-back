from unittest.mock import Mock
from uuid import uuid4

import pytest

from sidebrain_back.tasks import mentor_dispatch_task


def test_broker_failure_allows_redelivery_on_next_dispatch(monkeypatch):
    user_id, generation_id = str(uuid4()), str(uuid4())

    async def queued():
        return [(user_id, generation_id)]

    publish = Mock(side_effect=[ConnectionError("broker"), None])
    monkeypatch.setattr(mentor_dispatch_task, "_collect_pending", queued)
    monkeypatch.setattr(
        mentor_dispatch_task.generate_mentor_task, "delay", publish
    )

    with pytest.raises(ConnectionError):
        mentor_dispatch_task.dispatch_mentor_task.run()
    mentor_dispatch_task.dispatch_mentor_task.run()
    assert publish.call_count == 2
    assert publish.call_args.args == (user_id, generation_id)
