"""5-layer progress logging pipeline."""
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.generated_roadmap import GeneratedRoadmap, KnowledgeBase
from app.models.roadmap_enrollment import RoadmapEnrollment, TopicProgressLog
from app.services.chroma_service import index_knowledge_base, get_topic_relevance
from app.services.llm_client import async_chat_complete, extract_and_parse_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/roadmaps", tags=["Roadmap Progress v3"])


class LogProgressRequest(BaseModel):
    log_text: str = Field(..., min_length=20, max_length=2000)


# --- Enrollment ---

@router.post("/{roadmap_id}/enroll")
async def enroll_in_roadmap(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check roadmap exists
    rm_result = await db.execute(
        select(GeneratedRoadmap).where(GeneratedRoadmap.id == roadmap_id, GeneratedRoadmap.user_id == current_user.id)
    )
    rm = rm_result.scalar_one_or_none()
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    # Check if already enrolled
    enr_result = await db.execute(
        select(RoadmapEnrollment).where(
            RoadmapEnrollment.user_id == current_user.id,
            RoadmapEnrollment.roadmap_id == roadmap_id,
        )
    )
    enrollment = enr_result.scalar_one_or_none()
    if enrollment:
        return {"data": _enrollment_dict(enrollment, rm)}

    # Create enrollment
    enrollment = RoadmapEnrollment(user_id=current_user.id, roadmap_id=rm.id, completed_topic_ids=[])
    db.add(enrollment)
    await db.flush()

    # Index KB into ChromaDB
    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == rm.id))
    kb = kb_result.scalar_one_or_none()
    if kb and kb.data:
        try:
            index_knowledge_base(str(rm.id), kb.data)
        except Exception as e:
            logger.warning("[Enroll] ChromaDB indexing failed: %s", e)

    logger.info("[Enroll] User %s enrolled in roadmap %s", current_user.id, rm.id)
    return {"data": _enrollment_dict(enrollment, rm)}


@router.get("/{roadmap_id}/enrollment")
async def get_enrollment(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    enr_result = await db.execute(
        select(RoadmapEnrollment).where(
            RoadmapEnrollment.user_id == current_user.id,
            RoadmapEnrollment.roadmap_id == roadmap_id,
        )
    )
    enrollment = enr_result.scalar_one_or_none()
    if not enrollment:
        return {"data": None}

    rm_result = await db.execute(select(GeneratedRoadmap).where(GeneratedRoadmap.id == roadmap_id))
    rm = rm_result.scalar_one_or_none()
    return {"data": _enrollment_dict(enrollment, rm)}


# --- 5-layer progress logging ---

@router.post("/{roadmap_id}/topics/{topic_id}/log")
async def log_progress(
    roadmap_id: str,
    topic_id: str,
    request: LogProgressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    log_text = request.log_text.strip()

    # Get/create enrollment
    enr_result = await db.execute(
        select(RoadmapEnrollment).where(
            RoadmapEnrollment.user_id == current_user.id,
            RoadmapEnrollment.roadmap_id == roadmap_id,
        )
    )
    enrollment = enr_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this roadmap. Enroll first.")

    # --- LAYER 1: Rate limit (1 accepted log per topic per hour) ---
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_result = await db.execute(
        select(TopicProgressLog).where(
            TopicProgressLog.enrollment_id == enrollment.id,
            TopicProgressLog.topic_id == topic_id,
            TopicProgressLog.passed == True,
            TopicProgressLog.created_at > one_hour_ago,
        )
    )
    if recent_result.scalar_one_or_none():
        return _reject(db, enrollment, topic_id, log_text, "Rate limited: wait 1 hour between accepted logs for the same topic.")

    # --- LAYER 2: Length (already validated by Pydantic, but double-check) ---
    if len(log_text) < 20:
        return _reject(db, enrollment, topic_id, log_text, "Log too short. Minimum 20 characters.")

    # --- LAYER 3: Already completed ---
    completed = enrollment.completed_topic_ids or []
    if topic_id in completed:
        return _reject(db, enrollment, topic_id, log_text, "Topic already completed.")

    # --- LAYER 4: Relevance (ChromaDB cosine similarity >= 0.50) ---
    try:
        similarity = get_topic_relevance(str(roadmap_id), topic_id, log_text)
        logger.info("[Progress] Topic %s relevance score: %.3f", topic_id, similarity)
        if similarity < 0.50:
            return _reject(db, enrollment, topic_id, log_text, f"Log doesn't seem relevant to this topic (similarity: {similarity:.2f}). Be more specific about what you learned.")
    except Exception as e:
        logger.warning("[Progress] Relevance check failed: %s — skipping", e)

    # --- LAYER 5: LLM specificity check ---
    try:
        # Get topic title from roadmap
        rm_result = await db.execute(select(GeneratedRoadmap).where(GeneratedRoadmap.id == roadmap_id))
        rm = rm_result.scalar_one_or_none()
        topic_title = _find_topic_title(rm.roadmap_data if rm else {}, topic_id)

        specificity_prompt = f"""A student is logging progress for the topic "{topic_title}".
Their log: "{log_text}"

Is this log SPECIFIC enough? A good log mentions concrete concepts, tools, or techniques they learned.
A bad log is vague like "I learned stuff" or "it was interesting".

Return ONLY JSON: {{"specific": true}} or {{"specific": false, "reason": "brief explanation"}}"""

        raw = await async_chat_complete(
            [{"role": "system", "content": "You evaluate learning logs for specificity. Return only JSON."},
             {"role": "user", "content": specificity_prompt}],
            temperature=0.2, max_tokens=200,
        )
        result = extract_and_parse_json(raw)
        if not result.get("specific", True):
            reason = result.get("reason", "Log is too vague. Describe specific concepts or skills you learned.")
            return _reject(db, enrollment, topic_id, log_text, f"Not specific enough: {reason}")
    except Exception as e:
        logger.warning("[Progress] Specificity check failed: %s — accepting anyway", e)

    # --- ALL LAYERS PASSED — Accept ---
    log_entry = TopicProgressLog(
        enrollment_id=enrollment.id,
        topic_id=topic_id,
        log_text=log_text,
        passed=True,
    )
    db.add(log_entry)

    # Mark topic as completed
    new_completed = list(completed) + [topic_id]
    enrollment.completed_topic_ids = new_completed
    await db.flush()

    total_topics = _count_total_topics(rm.roadmap_data if rm else {})
    logger.info("[Progress] Topic %s ACCEPTED for enrollment %s (%d/%d)", topic_id, enrollment.id, len(new_completed), total_topics)

    return {
        "accepted": True,
        "topic_id": topic_id,
        "completed_topics": len(new_completed),
        "total_topics": total_topics,
    }


def _reject(db, enrollment, topic_id, log_text, reason):
    """Helper to log a rejected progress entry."""
    log_entry = TopicProgressLog(
        enrollment_id=enrollment.id,
        topic_id=topic_id,
        log_text=log_text,
        passed=False,
        rejection_reason=reason,
    )
    db.add(log_entry)
    return {"accepted": False, "topic_id": topic_id, "reason": reason}


def _find_topic_title(roadmap_data: dict, topic_id: str) -> str:
    for phase in roadmap_data.get("phases", []):
        for sa in phase.get("skill_areas", []):
            for topic in sa.get("topics", []):
                if topic.get("topic_id") == topic_id:
                    return topic.get("title", topic_id)
    return topic_id


def _count_total_topics(roadmap_data: dict) -> int:
    count = 0
    for phase in roadmap_data.get("phases", []):
        for sa in phase.get("skill_areas", []):
            count += len(sa.get("topics", []))
    return count


def _enrollment_dict(enrollment: RoadmapEnrollment, rm: GeneratedRoadmap | None) -> dict:
    total = _count_total_topics(rm.roadmap_data if rm else {})
    completed = enrollment.completed_topic_ids or []
    return {
        "id": str(enrollment.id),
        "roadmap_id": str(enrollment.roadmap_id),
        "completed_topic_ids": completed,
        "total_topics": total,
        "progress_pct": round(len(completed) / total * 100, 1) if total > 0 else 0,
        "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
    }
