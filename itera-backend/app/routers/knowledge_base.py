"""
Knowledge base CRUD endpoints.
Allows viewing and editing KB entries per topic, and triggering LLM regeneration.
"""
import hashlib
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.generated_roadmap import GeneratedRoadmap, KnowledgeBase
from app.services.chroma_service import reindex_single_topic
from app.services.roadmap_service import _generate_single_topic_kb, _slugify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/roadmaps", tags=["Knowledge Base v3"])


def _find_topic_meta(roadmap_data: dict, topic_id: str) -> dict:
    """Return minimal topic metadata from roadmap_data by topic_id."""
    for phase in roadmap_data.get("phases", []):
        for sa in phase.get("skill_areas", []):
            for topic in sa.get("topics", []):
                if topic.get("topic_id") == topic_id:
                    return {
                        "topic": topic,
                        "section_name": sa.get("title", ""),
                        "section_id": _slugify(sa.get("title", "")),
                    }
    return {}


# --- GET full KB ---

@router.get("/{roadmap_id}/knowledge-base")
async def get_knowledge_base(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rm_result = await db.execute(
        select(GeneratedRoadmap).where(
            GeneratedRoadmap.id == roadmap_id,
            GeneratedRoadmap.user_id == current_user.id,
        )
    )
    if not rm_result.scalar_one_or_none():
        raise HTTPException(404, "Roadmap not found")

    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap_id))
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "Knowledge base not found for this roadmap")

    return {"data": kb.data}


# --- GET single topic KB entry ---

@router.get("/{roadmap_id}/knowledge-base/{topic_id}")
async def get_kb_entry(
    roadmap_id: str,
    topic_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rm_result = await db.execute(
        select(GeneratedRoadmap).where(
            GeneratedRoadmap.id == roadmap_id,
            GeneratedRoadmap.user_id == current_user.id,
        )
    )
    if not rm_result.scalar_one_or_none():
        raise HTTPException(404, "Roadmap not found")

    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap_id))
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    entry = next((t for t in kb.data.get("topics", []) if t.get("topic_id") == topic_id), None)
    if not entry:
        raise HTTPException(404, f"Topic {topic_id} not found in knowledge base")

    return {"data": entry}


# --- PATCH single topic KB entry ---

@router.patch("/{roadmap_id}/knowledge-base/{topic_id}")
async def update_kb_entry(
    roadmap_id: str,
    topic_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rm_result = await db.execute(
        select(GeneratedRoadmap).where(
            GeneratedRoadmap.id == roadmap_id,
            GeneratedRoadmap.user_id == current_user.id,
        )
    )
    if not rm_result.scalar_one_or_none():
        raise HTTPException(404, "Roadmap not found")

    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap_id))
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    topics = kb.data.get("topics", [])
    topic_entry = next((t for t in topics if t.get("topic_id") == topic_id), None)
    if not topic_entry:
        raise HTTPException(404, f"Topic {topic_id} not found in knowledge base")

    # Merge update into the knowledge field
    if "knowledge" in body:
        if "knowledge" not in topic_entry:
            topic_entry["knowledge"] = {}
        topic_entry["knowledge"].update(body["knowledge"])

    # Recalculate version_hash
    content_str = json.dumps(topic_entry.get("knowledge", {}), sort_keys=True)
    topic_entry["version_hash"] = hashlib.md5(content_str.encode()).hexdigest()[:16]
    topic_entry["generation_status"] = "manual_edit"

    # Trigger SQLAlchemy change detection on JSON column
    flag_modified(kb, "data")
    await db.commit()

    # Re-index in ChromaDB
    try:
        reindex_single_topic(str(roadmap_id), topic_id, topic_entry)
        logger.info("[KB] Re-indexed topic %s in roadmap %s after edit", topic_id, roadmap_id)
    except Exception as e:
        logger.warning("[KB] ChromaDB re-index failed after edit: %s", e)

    return {"status": "updated", "topic_id": topic_id, "version_hash": topic_entry["version_hash"]}


# --- POST regenerate single topic KB entry ---

@router.post("/{roadmap_id}/knowledge-base/{topic_id}/regenerate")
async def regenerate_kb_entry(
    roadmap_id: str,
    topic_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rm_result = await db.execute(
        select(GeneratedRoadmap).where(
            GeneratedRoadmap.id == roadmap_id,
            GeneratedRoadmap.user_id == current_user.id,
        )
    )
    rm = rm_result.scalar_one_or_none()
    if not rm:
        raise HTTPException(404, "Roadmap not found")

    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.roadmap_id == roadmap_id))
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    # Get topic metadata from roadmap
    meta = _find_topic_meta(rm.roadmap_data, topic_id)
    if not meta:
        raise HTTPException(404, f"Topic {topic_id} not found in roadmap")

    topic = meta["topic"]

    # Regenerate via LLM
    new_entry = await _generate_single_topic_kb(
        topic=topic,
        section_name=meta["section_name"],
        section_id=meta["section_id"],
        target_role=rm.target_role,
        domain=rm.roadmap_data.get("domain", "general"),
        roadmap_id=str(roadmap_id),
        db=db,
    )

    # Replace in KB topics list
    topics = kb.data.get("topics", [])
    for i, t in enumerate(topics):
        if t.get("topic_id") == topic_id:
            topics[i] = new_entry
            break
    else:
        topics.append(new_entry)

    flag_modified(kb, "data")
    await db.commit()

    # Re-index in ChromaDB
    try:
        reindex_single_topic(str(roadmap_id), topic_id, new_entry)
        logger.info("[KB] Re-indexed topic %s after regeneration", topic_id)
    except Exception as e:
        logger.warning("[KB] ChromaDB re-index failed after regeneration: %s", e)

    return {"status": "regenerated", "topic_id": topic_id, "generation_status": new_entry.get("generation_status"), "version_hash": new_entry.get("version_hash")}
