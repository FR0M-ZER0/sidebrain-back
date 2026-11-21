from sidebrain_back.core.database import engine
from sidebrain_back.tasks.mentor_generation_task import generate_mentor_task


def test_database_logs_hide_query_parameters():
    assert engine.sync_engine.hide_parameters is True


def test_mentor_worker_does_not_store_result():
    assert generate_mentor_task.ignore_result is True
