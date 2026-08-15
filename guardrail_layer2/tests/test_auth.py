import pytest

pytestmark = pytest.mark.asyncio


async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_login_success(client):
    from tests.conftest import settings

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"
    assert len(body["access_token"]) > 20


async def test_login_wrong_password(client):
    from tests.conftest import settings

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": "definitely-wrong"},
    )
    assert response.status_code == 401


async def test_login_unknown_user(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )
    assert response.status_code == 401


async def test_admin_route_requires_token(client):
    response = await client.get("/api/v1/admin/spend-dashboard")
    assert response.status_code == 401


async def test_admin_route_with_token(client, auth_headers):
    response = await client.get("/api/v1/admin/spend-dashboard", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "users" in body
    assert "policy_index_stats" in body
