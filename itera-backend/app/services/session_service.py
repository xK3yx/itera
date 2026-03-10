import json
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.config import get_settings
from app.models.session import Session
from app.models.message import Message
from app.models.roadmap import Roadmap

settings = get_settings()


def get_redis():
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def get_conversation_history(
    session_id: UUID,
    db: AsyncSession
) -> list[dict]:
    """Get conversation history from Redis cache or database."""
    try:
        redis = get_redis()
        try:
            cache_key = f"history:{session_id}"
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        finally:
            await redis.aclose()
    except Exception:
        pass

    # Fall back to database
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.order)
    )
    messages = result.scalars().all()

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]

    # Cache for 1 hour (best-effort)
    if history:
        try:
            redis = get_redis()
            try:
                cache_key = f"history:{session_id}"
                await redis.setex(cache_key, 3600, json.dumps(history))
            finally:
                await redis.aclose()
        except Exception:
            pass

    return history


async def save_message(
    session_id: UUID,
    role: str,
    content: str,
    order: int,
    db: AsyncSession
) -> Message:
    """Save a message to the database and update Redis cache."""
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        order=order
    )
    db.add(message)
    await db.flush()

    # Invalidate cache so it gets refreshed next time (best-effort)
    try:
        redis = get_redis()
        try:
            cache_key = f"history:{session_id}"
            await redis.delete(cache_key)
        finally:
            await redis.aclose()
    except Exception:
        pass

    return message


async def save_roadmap(
    session_id: UUID,
    roadmap_data: dict,
    db: AsyncSession
) -> Roadmap:
    """Save a generated roadmap to the database."""
    # Check if roadmap already exists
    result = await db.execute(
        select(Roadmap).where(Roadmap.session_id == session_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.goal = roadmap_data.get("goal", "")
        existing.total_estimated_hours = roadmap_data.get("total_estimated_hours", 0)
        existing.weekly_hours = roadmap_data.get("weekly_hours")
        existing.estimated_weeks = roadmap_data.get("estimated_weeks")
        existing.skill_areas = roadmap_data.get("skill_areas", [])
        return existing

    roadmap = Roadmap(
        session_id=session_id,
        goal=roadmap_data.get("goal", ""),
        total_estimated_hours=roadmap_data.get("total_estimated_hours", 0),
        weekly_hours=roadmap_data.get("weekly_hours"),
        estimated_weeks=roadmap_data.get("estimated_weeks"),
        skill_areas=roadmap_data.get("skill_areas", [])
    )
    db.add(roadmap)
    await db.flush()
    return roadmap