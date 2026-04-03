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
from app.services.llm_client import extract_and_parse_json
from app.services.llm_tracker import tracked_llm_call
from app.services.fuzzy_match import fuzzy_keyword_match

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

    # --- LAYER 4: Combined relevance — ChromaDB semantic + fuzzy keyword matching ---
    match_details = {}
    try:
        # 4a. ChromaDB semantic similarity
        semantic_score = get_topic_relevance(str(roadmap_id), topic_id, log_text)
        logger.info("[Progress] Topic %s semantic score: %.3f", topic_id, semantic_score)

        # 4b. Fuzzy keyword matching against KB validation_keywords
        keyword_result = {"match_percentage": 0.0, "matched_keywords": [], "unmatched_keywords": [], "total_keywords": 0, "matched_count": 0}
        try:
            kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap_id))
            kb = kb_result.scalar_one_or_none()
            if kb and kb.data:
                topics_list = kb.data.get("topics", [])
                topic_kb_entry = next((t for t in topics_list if t.get("topic_id") == topic_id), None)
                if topic_kb_entry:
                    keyword_result = fuzzy_keyword_match(log_text, topic_kb_entry)
                    logger.info("[Progress] Topic %s keyword match: %.1f%% (%d/%d)", topic_id, keyword_result["match_percentage"], keyword_result["matched_count"], keyword_result["total_keywords"])
        except Exception as kw_err:
            logger.warning("[Progress] Keyword match failed: %s", kw_err)

        # 4c. Combined score: semantic (60%) + keyword (40%)
        combined_score = (semantic_score * 0.6) + (keyword_result["match_percentage"] / 100.0 * 0.4)
        passes_relevance = combined_score >= 0.45 or keyword_result["match_percentage"] >= 15.0

        match_details = {
            "semantic_score": round(semantic_score, 4),
            "keyword_match_percentage": keyword_result["match_percentage"],
            "keywords_matched": keyword_result["matched_keywords"],
            "keywords_missed": keyword_result["unmatched_keywords"],
            "combined_score": round(combined_score, 4),
        }

        logger.info("[Progress] Topic %s combined_score=%.3f passes=%s", topic_id, combined_score, passes_relevance)

        if not passes_relevance:
            return _reject(
                db, enrollment, topic_id, log_text,
                f"Log doesn't seem relevant to this topic (combined score: {combined_score:.2f}). Be more specific about what you learned.",
                match_details=match_details,
            )
    except Exception as e:
        logger.warning("[Progress] Relevance check failed: %s — skipping", e)

    # --- LAYER 5: LLM specificity check (focused prompt — only topic context, no full roadmap) ---
    try:
        # Get topic title from roadmap
        rm_result = await db.execute(select(GeneratedRoadmap).where(GeneratedRoadmap.id == roadmap_id))
        rm = rm_result.scalar_one_or_none()
        topic_title = _find_topic_title(rm.roadmap_data if rm else {}, topic_id)

        # Pull KB context for a focused prompt (what_it_is + first 10 validation_keywords)
        what_it_is = ""
        kw_sample = []
        try:
            kb_result2 = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap_id))
            kb2 = kb_result2.scalar_one_or_none()
            if kb2 and kb2.data:
                topic_entry = next((t for t in kb2.data.get("topics", []) if t.get("topic_id") == topic_id), None)
                if topic_entry:
                    knowledge = topic_entry.get("knowledge", {})
                    what_it_is = knowledge.get("what_it_is", "")
                    kw_sample = knowledge.get("validation_keywords", [])[:10]
        except Exception:
            pass

        # Lean prompt — only topic name, brief description, key terms, and student log
        kw_line = f"Key concepts include: {', '.join(kw_sample)}." if kw_sample else ""
        what_line = f"This topic is about: {what_it_is}" if what_it_is else ""

        specificity_prompt = (
            f"A student is learning '{topic_title}'. {what_line} {kw_line}\n\n"
            f"The student wrote: \"{log_text}\"\n\n"
            f"Does their writing demonstrate they learned something specific about this topic? "
            f"A good log mentions concrete concepts, tools, or techniques. A bad log is vague like 'I learned stuff'.\n\n"
            f"Return ONLY JSON: {{\"specific\": true}} or {{\"specific\": false, \"reason\": \"brief explanation\"}}"
        )

        tracked_result = await tracked_llm_call(
            [{"role": "system", "content": "You evaluate learning logs for specificity. Return only JSON."},
             {"role": "user", "content": specificity_prompt}],
            call_type="specificity_check",
            roadmap_id=str(roadmap_id),
            topic_id=topic_id,
            temperature=0.2,
            max_tokens=200,
            db=db,
        )
        parsed = extract_and_parse_json(tracked_result["content"])

        # Attach LLM result to match_details
        match_details["llm_specificity_result"] = "YES" if parsed.get("specific", True) else "NO"
        match_details["llm_specificity_latency_ms"] = tracked_result.get("latency_ms")
        match_details["model_used"] = tracked_result.get("model")
        match_details["provider"] = tracked_result.get("provider")

        if not parsed.get("specific", True):
            reason = parsed.get("reason", "Log is too vague. Describe specific concepts or skills you learned.")
            return _reject(db, enrollment, topic_id, log_text, f"Not specific enough: {reason}", match_details=match_details)
    except Exception as e:
        logger.warning("[Progress] Specificity check failed: %s — accepting anyway", e)

    # --- ALL LAYERS PASSED — Accept ---
    log_entry = TopicProgressLog(
        enrollment_id=enrollment.id,
        topic_id=topic_id,
        log_text=log_text,
        passed=True,
        match_details=match_details if match_details else None,
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


def _reject(db, enrollment, topic_id, log_text, reason, match_details=None):
    """Helper to log a rejected progress entry."""
    log_entry = TopicProgressLog(
        enrollment_id=enrollment.id,
        topic_id=topic_id,
        log_text=log_text,
        passed=False,
        rejection_reason=reason,
        match_details=match_details,
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
