from sidebrain_back.core.celery_app import celery_app


def test_existing_celery_transport_is_unchanged() -> None:
    assert celery_app.conf.broker_url.startswith("redis://")
    assert celery_app.conf.result_backend.startswith("redis://")
    assert (
        "sidebrain_back.tasks.generate_track_task" in celery_app.conf.imports
    )
