from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.constants import Env


def test_notification_settings_have_safe_local_defaults() -> None:
    assert Env.RABBITMQ_HOST == "127.0.0.1"
    assert Env.RABBITMQ_PORT == 5672
    assert Env.RABBITMQ_MAX_ATTEMPTS == 5
    assert Env.RABBITMQ_USER
    assert Env.RABBITMQ_PASSWORD


def test_celery_configuration_remains_on_redis() -> None:
    assert celery_app.conf.broker_url.startswith("redis://")
    assert celery_app.conf.result_backend.startswith("redis://")
