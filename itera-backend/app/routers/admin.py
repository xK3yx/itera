"""
Admin / observability endpoints.
Tab A: LLM call logs
Tab B: Progress validation logs
Tab C: KB quality per roadmap
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.llm_call_log import LLMCallLog
from app.models.roadmap_enrollment import TopicProgressLog, RoadmapEnrollment
from app.models.generated_roadmap import GeneratedRoadmap, KnowledgeBase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/admin", tags=["Admin v3"])


# ---------- Utility: Re-index all roadmaps ----------

@router.post("/reindex-all")
async def reindex_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-index all roadmaps' KB entries in ChromaDB with the rich format."""
    from app.services.chroma_service import reindex_all_roadmaps
    await reindex_all_roadmaps(db)
    return {"status": "ok", "message": "Re-index complete. Check server logs for details."}


# ---------- A. LLM Call Logs ----------

@router.get("/llm-logs")
async def list_llm_logs(
    call_type: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    roadmap_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(LLMCallLog).order_by(LLMCallLog.created_at.desc())

    if call_type:
        q = q.where(LLMCallLog.call_type == call_type)
    if model:
        q = q.where(LLMCallLog.model_used == model)
    if roadmap_id:
        q = q.where(LLMCallLog.roadmap_id == roadmap_id)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar()

    rows = await db.execute(q.offset(offset).limit(limit))
    logs = rows.scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "data": [_format_llm_log(l) for l in logs],
    }


@router.get("/llm-logs/summary")
async def llm_logs_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            func.count(LLMCallLog.id).label("total_calls"),
            func.avg(LLMCallLog.latency_ms).label("avg_latency_ms"),
            func.sum(LLMCallLog.tokens_total).label("total_tokens"),
            func.sum(
                func.cast(LLMCallLog.parsed_successfully == False, db.bind.dialect.INTEGER if hasattr(db, 'bind') else "integer")  # noqa
            ).label("failed_calls"),
        )
    )
    # Simpler aggregation approach
    all_logs = await db.execute(select(LLMCallLog))
    logs = all_logs.scalars().all()

    total_calls = len(logs)
    failed_calls = sum(1 for l in logs if not l.parsed_successfully)
    total_tokens = sum((l.tokens_total or 0) for l in logs)
    avg_latency = round(sum((l.latency_ms or 0) for l in logs) / total_calls, 1) if total_calls else 0
    hallucination_count = sum(len(l.hallucination_flags or []) for l in logs)

    calls_by_type = {}
    tokens_by_model = {}
    for l in logs:
        calls_by_type[l.call_type] = calls_by_type.get(l.call_type, 0) + 1
        tokens_by_model[l.model_used] = tokens_by_model.get(l.model_used, 0) + (l.tokens_total or 0)

    return {
        "total_calls": total_calls,
        "failed_calls": failed_calls,
        "failure_rate": round(failed_calls / total_calls * 100, 1) if total_calls else 0,
        "avg_latency_ms": avg_latency,
        "total_tokens": total_tokens,
        "hallucination_count": hallucination_count,
        "calls_by_type": calls_by_type,
        "tokens_by_model": tokens_by_model,
    }


# ---------- B. Progress Validation Logs ----------

@router.get("/progress-logs")
async def list_progress_logs(
    roadmap_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    passed: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(TopicProgressLog, RoadmapEnrollment)
        .join(RoadmapEnrollment, TopicProgressLog.enrollment_id == RoadmapEnrollment.id)
        .order_by(TopicProgressLog.created_at.desc())
    )

    if roadmap_id:
        q = q.where(RoadmapEnrollment.roadmap_id == roadmap_id)
    if user_id:
        q = q.where(RoadmapEnrollment.user_id == user_id)
    if passed is not None:
        q = q.where(TopicProgressLog.passed == passed)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar()

    rows = await db.execute(q.offset(offset).limit(limit))
    items = rows.all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "data": [_format_progress_log(log, enrollment) for log, enrollment in items],
    }


# ---------- C. KB Quality Dashboard ----------

@router.get("/kb-quality/{roadmap_id}")
async def kb_quality(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap_id))
    kb = kb_result.scalar_one_or_none()
    if not kb:
        return {"data": [], "roadmap_id": roadmap_id}

    topics = kb.data.get("topics", [])

    # Get acceptance stats per topic_id
    enr_result = await db.execute(
        select(RoadmapEnrollment).where(RoadmapEnrollment.roadmap_id == roadmap_id)
    )
    enrollments = enr_result.scalars().all()
    enr_ids = [e.id for e in enrollments]

    topic_stats = {}
    if enr_ids:
        logs_result = await db.execute(
            select(TopicProgressLog).where(TopicProgressLog.enrollment_id.in_(enr_ids))
        )
        all_logs = logs_result.scalars().all()
        for log in all_logs:
            if log.topic_id not in topic_stats:
                topic_stats[log.topic_id] = {"accepted": 0, "rejected": 0}
            if log.passed:
                topic_stats[log.topic_id]["accepted"] += 1
            else:
                topic_stats[log.topic_id]["rejected"] += 1

    report = []
    for t in topics:
        tid = t.get("topic_id", "")
        knowledge = t.get("knowledge", {})
        kw_count = len(knowledge.get("validation_keywords", []))
        subtopic_count = len(knowledge.get("subtopics", []))
        learn_count = len(knowledge.get("what_you_will_learn", []))
        stats = topic_stats.get(tid, {"accepted": 0, "rejected": 0})

        report.append({
            "topic_id": tid,
            "topic_name": t.get("topic_name", t.get("title", tid)),
            "section_name": t.get("section_name", ""),
            "generation_status": t.get("generation_status", "unknown"),
            "version_hash": t.get("version_hash", ""),
            "keyword_count": kw_count,
            "subtopic_count": subtopic_count,
            "learn_item_count": learn_count,
            "thin_kb": kw_count < 10 or subtopic_count < 5,
            "accepted_logs": stats["accepted"],
            "rejected_logs": stats["rejected"],
            "total_logs": stats["accepted"] + stats["rejected"],
        })

    # Sort: thin KBs and failed ones first
    report.sort(key=lambda x: (x["generation_status"] != "failed", not x["thin_kb"], x["topic_id"]))

    return {"roadmap_id": roadmap_id, "topic_count": len(topics), "data": report}


# ---------- Formatters ----------

def _format_llm_log(l: LLMCallLog) -> dict:
    return {
        "id": str(l.id),
        "call_type": l.call_type,
        "model": l.model_used,
        "provider": l.provider,
        "latency_ms": l.latency_ms,
        "tokens_total": l.tokens_total,
        "parsed_successfully": l.parsed_successfully,
        "parse_attempts": l.parse_attempts,
        "hallucination_count": len(l.hallucination_flags or []),
        "hallucination_flags": l.hallucination_flags,
        "roadmap_id": str(l.roadmap_id) if l.roadmap_id else None,
        "topic_id": l.topic_id,
        "error_message": l.error_message,
        "prompt_messages": l.prompt_messages,
        "raw_response": l.raw_response,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }


def _format_progress_log(log: TopicProgressLog, enrollment: RoadmapEnrollment) -> dict:
    md = log.match_details or {}
    return {
        "id": str(log.id),
        "enrollment_id": str(log.enrollment_id),
        "roadmap_id": str(enrollment.roadmap_id),
        "user_id": str(enrollment.user_id),
        "topic_id": log.topic_id,
        "log_text": log.log_text,
        "passed": log.passed,
        "rejection_reason": log.rejection_reason,
        "semantic_score": md.get("semantic_score"),
        "keyword_match_percentage": md.get("keyword_match_percentage"),
        "combined_score": md.get("combined_score"),
        "keywords_matched": md.get("keywords_matched", []),
        "keywords_missed": md.get("keywords_missed", []),
        "llm_specificity_result": md.get("llm_specificity_result"),
        "llm_specificity_latency_ms": md.get("llm_specificity_latency_ms"),
        "model_used": md.get("model_used"),
        "provider": md.get("provider"),
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
