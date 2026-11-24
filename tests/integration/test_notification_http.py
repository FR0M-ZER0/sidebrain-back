from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sidebrain_back.core.database import get_db
from sidebrain_back.models.notification_model import Notification
from sidebrain_back.repositories.notification_repository import (
    NotificationRepository,
)
from sidebrain_back.routers.v1.auth_router import get_current_user


@pytest.mark.anyio
async def test_notifications_require_authentication(test_app):
    test_app.dependency_overrides.pop(get_current_user)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/v1/notifications")).status_code == 401
        assert (
            await client.patch(f"/api/v1/notifications/{uuid4()}/read")
        ).status_code == 401


@pytest.mark.anyio
async def test_notifications_are_private_paginated_and_read_idempotently(
    db_session, user_factory, test_app
):
    user, other = await user_factory(), await user_factory()
    repo = NotificationRepository(db_session)
    for index in range(3):
        repo.create(
            user_id=user.usr_id,
            event_key=f"test:{index}",
            type="test",
            title="Teste",
            message="Mensagem",
            destination=None,
        )
    await db_session.commit()

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        usr_id=user.usr_id
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/notifications?limit=2")
        assert response.status_code == 200
        assert response.json()["unread_count"] == 3
        assert len(response.json()["items"]) == 2
        notification_id = response.json()["items"][0]["id"]
        assert (
            len(
                (
                    await client.get("/api/v1/notifications?limit=2&offset=2")
                ).json()["items"]
            )
            == 1
        )
        test_app.dependency_overrides[get_current_user] = lambda: (
            SimpleNamespace(usr_id=other.usr_id)
        )
        assert (await client.get("/api/v1/notifications")).json() == {
            "items": [],
            "unread_count": 0,
        }
        assert (
            await client.patch(f"/api/v1/notifications/{notification_id}/read")
        ).status_code == 404
        test_app.dependency_overrides[get_current_user] = lambda: (
            SimpleNamespace(usr_id=user.usr_id)
        )
        assert (
            await client.patch(f"/api/v1/notifications/{notification_id}/read")
        ).status_code == 204
        first = (await client.get("/api/v1/notifications")).json()
        assert first["unread_count"] == 2
        read_at = next(
            item["read_at"]
            for item in first["items"]
            if item["id"] == notification_id
        )
        assert read_at is not None
        assert (
            await client.patch(f"/api/v1/notifications/{notification_id}/read")
        ).status_code == 204
        second = (await client.get("/api/v1/notifications")).json()
        assert (
            next(
                item["read_at"]
                for item in second["items"]
                if item["id"] == notification_id
            )
            == read_at
        )
        assert (
            await client.patch(f"/api/v1/notifications/{uuid4()}/read")
        ).status_code == 404
        assert (
            await client.get("/api/v1/notifications?limit=101")
        ).status_code == 422


@pytest.mark.anyio
async def test_notification_is_transactional_and_event_key_is_unique(
    db_session, user_factory
):
    user = await user_factory()
    user_id = user.usr_id
    await db_session.commit()
    repo = NotificationRepository(db_session)
    data = dict(
        user_id=user_id,
        event_key="test:1",
        type="test",
        title="Teste",
        message="Mensagem",
        destination=None,
    )
    repo.create(**data)
    await db_session.flush()
    await db_session.rollback()
    assert (
        await db_session.scalar(
            select(Notification).where(Notification.user_id == user_id)
        )
        is None
    )
    repo.create(**data)
    await db_session.flush()
    repo.create(**data)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
