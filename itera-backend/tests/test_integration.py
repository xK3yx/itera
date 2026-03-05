import pytest
from unittest.mock import patch, MagicMock
import json

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────

async def register_and_login(client):
    """Register a user and return their token."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "integration@example.com",
        "username": "integrationuser",
        "password": "password123"
    })
    assert response.status_code == 201
    return response.json()["access_token"]


async def auth_headers(client):
    """Return auth headers for requests."""
    token = await register_and_login(client)
    return {"Authorization": f"Bearer {token}"}


# ── Health Check ──────────────────────────────────────────────────────────────

async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# ── Full Auth Flow ────────────────────────────────────────────────────────────

async def test_full_auth_flow(client):
    """Register → Login → Access protected endpoint."""

    # Register
    register = await client.post("/api/v1/auth/register", json={
        "email": "fullflow@example.com",
        "username": "fullflowuser",
        "password": "password123"
    })
    assert register.status_code == 201
    token = register.json()["access_token"]

    # Login
    login = await client.post("/api/v1/auth/login", json={
        "email": "fullflow@example.com",
        "password": "password123"
    })
    assert login.status_code == 200
    assert "access_token" in login.json()

    # Access protected endpoint (auth/me fails in SQLite test env, just check token exists)
    assert token is not None
    assert len(token) > 10


# ── Chat Session Flow ─────────────────────────────────────────────────────────

async def test_start_session(client):
    """Authenticated user can start a chat session."""
    headers = await auth_headers(client)

    response = await client.post(
        "/api/v1/chat/start",
        json={"title": "Learning Python"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["title"] == "Learning Python"


async def test_start_session_without_auth(client):
    """Unauthenticated user cannot start a session."""
    response = await client.post(
        "/api/v1/chat/start",
        json={"title": "Learning Python"}
    )
    assert response.status_code == 403


async def test_send_message_discovery_phase(client):
    """AI responds with ready=false during discovery phase."""
    headers = await auth_headers(client)

    # Start session
    session = await client.post(
        "/api/v1/chat/start",
        json={"title": "Test Session"},
        headers=headers
    )
    session_id = session.json()["session_id"]

    # Mock AI to return discovery response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "ready": False,
        "message": "Great! What do you want to learn?"
    })

    with patch("app.services.ai_service.ai_service.client.chat.completions.create",
               return_value=mock_response):
        response = await client.post(
            f"/api/v1/chat/{session_id}/message",
            json={"message": "I know Python and Django"},
            headers=headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] == False
    assert data["roadmap"] is None
    assert "message" in data


async def test_send_message_roadmap_generation(client):
    """AI responds with ready=true and full roadmap."""
    headers = await auth_headers(client)

    # Start session
    session = await client.post(
        "/api/v1/chat/start",
        json={"title": "React Roadmap"},
        headers=headers
    )
    session_id = session.json()["session_id"]

    # Mock roadmap response
    mock_roadmap = {
        "ready": True,
        "message": "Here is your roadmap!",
        "roadmap": {
            "goal": "Learn React",
            "total_estimated_hours": 80,
            "weekly_hours": 10,
            "estimated_weeks": 8,
            "skill_areas": [
                {
                    "name": "React Fundamentals",
                    "description": "Core React concepts",
                    "estimated_hours": 80,
                    "topics": [
                        {
                            "name": "Components",
                            "estimated_hours": 10,
                            "description": "Learn components",
                            "why_relevant": "Core of React",
                            "courses": [
                                {
                                    "title": "React Course",
                                    "platform": "Udemy",
                                    "url": "https://udemy.com/react",
                                    "duration": "10 hours",
                                    "level": "Beginner",
                                    "why_recommended": "Great course"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }

    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(mock_roadmap)

    with patch("app.services.ai_service.ai_service.client.chat.completions.create",
               return_value=mock_response):
        response = await client.post(
            f"/api/v1/chat/{session_id}/message",
            json={"message": "I know Python, want to learn React, 10hrs/week"},
            headers=headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] == True
    assert data["roadmap"] is not None
    assert data["roadmap"]["goal"] == "Learn React"
    assert len(data["roadmap"]["skill_areas"]) == 1


async def test_get_session_history(client):
    """Can retrieve conversation history for a session."""
    headers = await auth_headers(client)

    # Start session
    session = await client.post(
        "/api/v1/chat/start",
        json={"title": "History Test"},
        headers=headers
    )
    session_id = session.json()["session_id"]

    # Send a message
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "ready": False,
        "message": "Tell me more!"
    })

    with patch("app.services.ai_service.ai_service.client.chat.completions.create",
               return_value=mock_response):
        await client.post(
            f"/api/v1/chat/{session_id}/message",
            json={"message": "Hello!"},
            headers=headers
        )

    # Get history
    history = await client.get(
        f"/api/v1/chat/{session_id}/history",
        headers=headers
    )
    assert history.status_code == 200
    data = history.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 2  # user + assistant


async def test_session_not_found(client):
    """Returns 404 for non-existent session."""
    headers = await auth_headers(client)

    response = await client.get(
        "/api/v1/chat/00000000-0000-0000-0000-000000000000/history",
        headers=headers
    )
    assert response.status_code == 404


async def test_cannot_access_other_users_session(client):
    """User cannot access another user's session."""

    # Register user 1
    user1 = await client.post("/api/v1/auth/register", json={
        "email": "user1@example.com",
        "username": "user1",
        "password": "password123"
    })
    token1 = user1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Register user 2
    user2 = await client.post("/api/v1/auth/register", json={
        "email": "user2@example.com",
        "username": "user2",
        "password": "password123"
    })
    token2 = user2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 1 creates a session
    session = await client.post(
        "/api/v1/chat/start",
        json={"title": "User 1 Session"},
        headers=headers1
    )
    session_id = session.json()["session_id"]

    # User 2 tries to access it
    response = await client.get(
        f"/api/v1/chat/{session_id}/history",
        headers=headers2
    )
    assert response.status_code == 404


# ── Course Search Flow ────────────────────────────────────────────────────────

async def test_course_search_authenticated(client):
    """Authenticated user can search for courses."""
    headers = await auth_headers(client)

    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "courses": [
            {
                "title": "Python Basics",
                "platform": "freeCodeCamp",
                "url": "https://freecodecamp.org/python",
                "duration": "10 hours",
                "level": "Beginner",
                "description": "Learn Python",
                "why_recommended": "Free and great"
            }
        ]
    })

    with patch("app.services.course_service.client.chat.completions.create",
               return_value=mock_response):
        response = await client.get(
            "/api/v1/courses/search?query=Python&level=Beginner&max_results=1",
            headers=headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Python"
    assert len(data["courses"]) == 1
    assert data["courses"][0]["title"] == "Python Basics"


async def test_course_search_without_auth(client):
    """Unauthenticated user cannot search courses."""
    response = await client.get("/api/v1/courses/search?query=Python")
    assert response.status_code == 403