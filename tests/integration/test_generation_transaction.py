from sidebrain_back.services.generation_errors import (
    GenerationPersistenceError,
)


def test_persistence_failures_have_public_error_code():
    error = GenerationPersistenceError()

    assert error.code == "generation_persistence_failed"
    assert "SQL" not in error.detail