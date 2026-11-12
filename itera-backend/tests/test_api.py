"""Tests for the v3 roadmap, progress, and admin endpoints."""
import uuid
from unittest.mock import patch

import pytest

from app.models.generated_roadmap import GeneratedRoadmap
from tests.conftest import register

pytestmark = pytest.mark.asyncio

SAMPLE_ROADMAP_DATA = {
    "phases": [
        {
            "id": "p1",
            "title": "Foundations",
            "skill_areas": [
                {"id": "p1-s1", "title": "Python", "topics": [{"id": "t1", "title": "Variables"}]}
            ],
        }
    ]
}


async def _fake_generate(*, db, user, target_role, learning_goal, interests, hours_per_week, include_paid):
    rm = GeneratedRoadmap(
        user_id=user.id,
        title=f"{target_role} roadmap",
        target_role=target_role,
        learning_goal=learning_goal,
        interests=interests,
        hours_per_week=hours_per_week,
        include_paid=include_paid,
        total_estimated_hours=10,
        roadmap_data=SAMPLE_ROADMAP_DATA,
    )
    db.add(rm)
    await db.flush()
    return rm


async def _generate(client, headers, role="Backend Developer"):
    with patch("app.routers.generated_roadmaps._generate_roadmap", side_effect=_fake_generate):
        res = await client.post(
            "/api/v3/roadmaps/generate",
            json={"target_role": role, "learning_goal": "Get job-ready for backend roles"},
            headers=headers,
        )
    assert res.status_code == 201, res.text
    return res.json()["data"]


async def test_health_reports_app_version(client):
    from app.main import APP_VERSION

    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "app": "Itera", "version": APP_VERSION}


async def test_generate_list_get_delete_roadmap(client):
    headers = await register(client)
    created = await _generate(client, headers)
    assert created["target_role"] == "Backend Developer"

    listed = await client.get("/api/v3/roadmaps/", headers=headers)
    assert [r["id"] for r in listed.json()["data"]] == [created["id"]]

    fetched = await client.get(f"/api/v3/roadmaps/{created['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["data"]["roadmap_data"] == SAMPLE_ROADMAP_DATA

    deleted = await client.delete(f"/api/v3/roadmaps/{created['id']}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v3/roadmaps/{created['id']}", headers=headers)
    assert missing.status_code == 404


async def test_generation_failure_does_not_leak_internals(client):
    headers = await register(client)
    with patch(
        "app.routers.generated_roadmaps._generate_roadmap",
        side_effect=RuntimeError("postgres password=hunter2"),
    ):
        res = await client.post(
            "/api/v3/roadmaps/generate",
            json={"target_role": "Data Engineer", "learning_goal": "Learn data pipelines well"},
            headers=headers,
        )
    assert res.status_code == 502
    assert "hunter2" not in res.text


async def test_users_cannot_access_each_others_roadmaps(client):
    alice = await register(client, "alice@example.com", "alice")
    bob = await register(client, "bob@example.com", "bob")
    roadmap = await _generate(client, alice)

    assert (await client.get(f"/api/v3/roadmaps/{roadmap['id']}", headers=bob)).status_code == 404
    assert (await client.delete(f"/api/v3/roadmaps/{roadmap['id']}", headers=bob)).status_code == 404
    assert (await client.post(f"/api/v3/roadmaps/{roadmap['id']}/enroll", headers=bob)).status_code == 404
    assert (await client.get("/api/v3/roadmaps/", headers=bob)).json()["data"] == []


async def test_invalid_roadmap_id_is_rejected(client):
    headers = await register(client)
    res = await client.get("/api/v3/roadmaps/not-a-uuid", headers=headers)
    assert res.status_code == 422


async def test_unknown_roadmap_returns_404(client):
    headers = await register(client)
    res = await client.get(f"/api/v3/roadmaps/{uuid.uuid4()}", headers=headers)
    assert res.status_code == 404


async def test_enroll_and_read_enrollment(client):
    headers = await register(client)
    roadmap = await _generate(client, headers)

    enrolled = await client.post(f"/api/v3/roadmaps/{roadmap['id']}/enroll", headers=headers)
    assert enrolled.status_code in (200, 201), enrolled.text

    enrollment = await client.get(f"/api/v3/roadmaps/{roadmap['id']}/enrollment", headers=headers)
    assert enrollment.status_code == 200, enrollment.text


async def test_roadmap_endpoints_require_auth(client):
    res = await client.get("/api/v3/roadmaps/")
    assert res.status_code in (401, 403)


async def test_admin_endpoints_reject_regular_users(client):
    headers = await register(client)
    for path in ("/api/v3/admin/llm-logs", "/api/v3/admin/progress-logs"):
        res = await client.get(path, headers=headers)
        assert res.status_code == 403, path
    res = await client.post("/api/v3/admin/reindex-all", headers=headers)
    assert res.status_code == 403


async def test_admin_endpoints_allow_configured_admin(client):
    headers = await register(client, "admin@example.com", "admin")
    res = await client.get("/api/v3/admin/llm-logs", headers=headers)
    assert res.status_code == 200, res.text
