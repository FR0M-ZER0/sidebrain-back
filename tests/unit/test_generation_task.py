from uuid import uuid4

from sidebrain_back.tasks.generate_track_task import generate_track_task


def test_generation_task_rejects_invalid_input_without_calling_ai():
    result = generate_track_task.run(
        request_id=str(uuid4()),
        user_id=str(uuid4()),
        goal="",
        topic="Python",
    )

    assert result["status"] == "failed"
    assert result["error_code"] == "generation_input_invalid"