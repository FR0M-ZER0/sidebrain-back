import importlib
from uuid import uuid4

from groq import GroqError

from sidebrain_back.tasks.generate_track_task import generate_track_task

generation_task_module = importlib.import_module(
    "sidebrain_back.tasks.generate_track_task"
)


def test_generation_task_rejects_invalid_input_without_calling_ai():
    result = generate_track_task.run(
        request_id=str(uuid4()),
        user_id=str(uuid4()),
        goal="",
        topic="Python",
    )

    assert result["status"] == "failed"
    assert result["error_code"] == "generation_input_invalid"


def test_generation_task_marks_groq_errors_as_failed(monkeypatch):
    request_id = uuid4()
    user_id = uuid4()
    marked_failed = []

    async def fail_generation(_payload):
        raise GroqError("Access denied")

    async def mark_failed(failed_request_id, error_code):
        marked_failed.append((failed_request_id, error_code))

    monkeypatch.setattr(
        generation_task_module, "_run_generation", fail_generation
    )
    monkeypatch.setattr(generation_task_module, "_mark_failed", mark_failed)

    result = generate_track_task.run(
        request_id=str(request_id),
        user_id=str(user_id),
        goal="Aprender Python",
        topic="Python",
    )

    assert result["status"] == "failed"
    assert result["error_code"] == "generation_provider_failed"
    assert marked_failed == [(request_id, "generation_provider_failed")]
