import pytest

from sidebrain_back.core.constants import Env


def test_operational_flow_requires_explicit_rabbitmq_environment() -> None:
    import os

    if os.getenv("RUN_RABBITMQ_TESTS") != "1":
        pytest.skip("defina RUN_RABBITMQ_TESTS=1 para validar o broker local")

    assert Env.RABBITMQ_HOST
    assert Env.RABBITMQ_PORT
