from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.session import Session
from app.models.roadmap import Roadmap
from app.middleware.auth_middleware import get_current_user
from app.schemas.roadmap import RoadmapResponse, SkillAreaSchema, TopicSchema, CourseSchema, SessionRoadmapResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/v1/roadmap", tags=["Roadmap"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_skill_areas(roadmap):
    """Parse skill_areas JSONB into schema objects."""
    skill_areas = []
    for area in roadmap.skill_areas:
        topics = []
        for topic in area.get("topics", []):
            courses = [CourseSchema(**course) for course in topic.get("courses", [])]
            topics.append(TopicSchema(
                name=topic.get("name", ""),
                estimated_hours=topic.get("estimated_hours", 0),
                description=topic.get("description", ""),
                why_relevant=topic.get("why_relevant"),
                courses=courses
            ))
        skill_areas.append(SkillAreaSchema(
            name=area.get("name", ""),
            description=area.get("description", ""),
            estimated_hours=area.get("estimated_hours", 0),
            topics=topics
        ))
    return skill_areas


async def _get_session_and_roadmap(session_id: UUID, user_id, db: AsyncSession):
    """Fetch session (verifying ownership) and its roadmap."""
    session_result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    roadmap_result = await db.execute(
        select(Roadmap).where(Roadmap.session_id == session_id)
    )
    roadmap = roadmap_result.scalar_one_or_none()
    if not roadmap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")

    return session, roadmap


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ProgressUpdateRequest(BaseModel):
    completed_topics: List[str]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[SessionRoadmapResponse])
async def get_all_roadmaps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all roadmaps for the current user."""

    # Single JOIN query — eliminates N+1
    result = await db.execute(
        select(Session, Roadmap)
        .join(Roadmap, Roadmap.session_id == Session.id)
        .where(Session.user_id == current_user.id)
        .order_by(Session.created_at.desc())
    )
    rows = result.all()

    return [
        SessionRoadmapResponse(
            session_id=session.id,
            session_title=session.title,
            status=session.status,
            roadmap=RoadmapResponse(
                roadmap_id=roadmap.id,
                session_id=roadmap.session_id,
                goal=roadmap.goal,
                total_estimated_hours=roadmap.total_estimated_hours,
                weekly_hours=roadmap.weekly_hours,
                estimated_weeks=roadmap.estimated_weeks,
                skill_areas=_build_skill_areas(roadmap),
                created_at=roadmap.created_at
            )
        )
        for session, roadmap in rows
    ]


@router.get("/{session_id}", response_model=SessionRoadmapResponse)
async def get_roadmap(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the generated learning roadmap for a session."""

    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    roadmap_result = await db.execute(
        select(Roadmap).where(Roadmap.session_id == session_id)
    )
    roadmap = roadmap_result.scalar_one_or_none()

    if not roadmap:
        return SessionRoadmapResponse(
            session_id=session.id,
            session_title=session.title,
            status=session.status,
            roadmap=None
        )

    roadmap_response = RoadmapResponse(
        roadmap_id=roadmap.id,
        session_id=roadmap.session_id,
        goal=roadmap.goal,
        total_estimated_hours=roadmap.total_estimated_hours,
        weekly_hours=roadmap.weekly_hours,
        estimated_weeks=roadmap.estimated_weeks,
        skill_areas=_build_skill_areas(roadmap),
        created_at=roadmap.created_at
    )

    return SessionRoadmapResponse(
        session_id=session.id,
        session_title=session.title,
        status=session.status,
        roadmap=roadmap_response
    )


@router.patch("/{session_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def update_progress(
    session_id: UUID,
    request: ProgressUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist completed topic keys for a roadmap (Feature 2)."""
    _, roadmap = await _get_session_and_roadmap(session_id, current_user.id, db)

    roadmap.completed_topics = request.completed_topics
    flag_modified(roadmap, "completed_topics")
    await db.commit()


@router.post("/{session_id}/adapt")
async def adapt_roadmap(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the roadmap removing completed topics (Feature 4)."""
    _, roadmap = await _get_session_and_roadmap(session_id, current_user.id, db)

    completed_keys = roadmap.completed_topics or []
    if not completed_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No completed topics to adapt from",
        )

    # Build roadmap dict for AI
    roadmap_dict = {
        "goal": roadmap.goal,
        "total_estimated_hours": roadmap.total_estimated_hours,
        "weekly_hours": roadmap.weekly_hours,
        "estimated_weeks": roadmap.estimated_weeks,
        "skill_areas": roadmap.skill_areas,
    }

    result = await ai_service.generate_adapted_roadmap(
        original_roadmap=roadmap_dict,
        completed_topic_keys=completed_keys,
        goal=roadmap.goal,
    )

    if not result.get("ready") or not result.get("roadmap"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to adapt roadmap"),
        )

    new_data = result["roadmap"]

    # Update roadmap columns
    roadmap.skill_areas = new_data.get("skill_areas", roadmap.skill_areas)
    roadmap.total_estimated_hours = new_data.get("total_estimated_hours", roadmap.total_estimated_hours)
    roadmap.weekly_hours = new_data.get("weekly_hours", roadmap.weekly_hours)
    roadmap.estimated_weeks = new_data.get("estimated_weeks", roadmap.estimated_weeks)
    roadmap.completed_topics = []

    flag_modified(roadmap, "skill_areas")
    flag_modified(roadmap, "completed_topics")
    await db.commit()

    return {"roadmap": new_data, "message": result.get("message", "Roadmap updated!")}
