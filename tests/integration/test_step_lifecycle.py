from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.repositories.step_repository import StepRepository


@pytest.mark.anyio
async def test_soft_delete_preserves_children_and_sets_terminal_fields():
    repository = StepRepository(SimpleNamespace())
    step = SimpleNamespace(
        stp_is_deleted=False,
        stp_deleted_at=None,
        stp_updated_at=datetime(2026, 1, 1),
        lessons=[SimpleNamespace(lsn_id=uuid4())],
        missions=[SimpleNamespace(msn_id=uuid4())],
    )

    await repository.soft_delete(step)

    assert step.stp_is_deleted is True
    assert step.stp_deleted_at == step.stp_updated_at
    assert len(step.lessons) == 1
    assert len(step.missions) == 1
