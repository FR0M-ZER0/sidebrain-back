from fastapi.testclient import TestClient

from main import create_app


def test_cors_allows_any_origin():
    client = TestClient(create_app())

    response = client.options(
        "/",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
