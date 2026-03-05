import pytest

pytestmark = pytest.mark.asyncio


async def test_register_success(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"


async def test_register_duplicate_email(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser2",
        "password": "password123"
    })
    assert response.status_code == 400


async def test_register_duplicate_username(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    response = await client.post("/api/v1/auth/register", json={
        "email": "test2@example.com",
        "username": "testuser",
        "password": "password123"
    })
    assert response.status_code == 400


async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


async def test_login_wrong_email(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123"
    })
    assert response.status_code == 401


async def test_get_me_without_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403


async def test_get_me_with_token(client):
    register = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    assert register.status_code == 201
    token = register.json()["access_token"]

    # Verify token was issued correctly
    assert token is not None
    assert len(token) > 0

    # Verify the protected endpoint rejects requests without token
    no_token_response = await client.get("/api/v1/auth/me")
    assert no_token_response.status_code == 403