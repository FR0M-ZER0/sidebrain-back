import pytest
from fastapi.testclient import TestClient

from sidebrain_back.schemas.avatar_schema import (
    AvatarListResponse,
    AvatarResponse,
)
from sidebrain_back.services.avatar_service import get_avatar_service


class AvatarServiceDouble:
    async def list_active(self) -> AvatarListResponse:
        return AvatarListResponse(
            data=[
                AvatarResponse(
                    slug="cat",
                    name="Gato",
                    image_url="/static/avatars/cat.png",
                )
            ]
        )


def test_avatar_catalog_returns_active_options(test_app):
    test_app.dependency_overrides[get_avatar_service] = AvatarServiceDouble
    response = TestClient(test_app).get("/api/v1/avatars")
    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "slug": "cat",
                "name": "Gato",
                "imageUrl": "/static/avatars/cat.png",
            }
        ]
    }


def test_avatar_image_is_served_by_backend(test_app):
    response = TestClient(test_app).get("/static/avatars/default.png")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "slug",
    [
        "default",
        "cat",
        "dog",
        "fox",
        "bear",
        "rabbit",
        "panda",
        "owl",
        "penguin",
        "lion",
        "turtle",
    ],
)
def test_all_catalog_images_are_served(test_app, slug):
    response = TestClient(test_app).get(f"/static/avatars/{slug}.png")
    assert response.status_code == 200
