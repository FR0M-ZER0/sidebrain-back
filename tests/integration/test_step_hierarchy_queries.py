from uuid import uuid4

from sidebrain_back.repositories.step_repository import StepRepository


def test_step_repository_defines_grouped_hierarchy_loaders():
    options = StepRepository._hierarchy_options(uuid4())

    assert len(options) == 2
    assert all(option is not None for option in options)
