"""Knowledge-base generation must respect KB_CONCURRENCY (Groq rate limits)."""
import asyncio

import pytest

from app.config import get_settings
from app.services import roadmap_service

pytestmark = pytest.mark.asyncio


async def test_kb_generation_respects_concurrency_limit(monkeypatch):
    limit = get_settings().kb_concurrency
    running = 0
    peak = 0

    async def fake_topic_kb(**kwargs):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return {"topic_id": kwargs["topic"]["id"]}

    monkeypatch.setattr(roadmap_service, "_generate_single_topic_kb", fake_topic_kb)
    items = [
        {
            "topic": {"id": f"t{i}"},
            "section_name": "s",
            "section_id": "s1",
            "target_role": "r",
            "domain": "d",
        }
        for i in range(10)
    ]

    results = await roadmap_service._generate_all_kb_entries(items)

    assert len(results) == 10
    assert peak == limit
