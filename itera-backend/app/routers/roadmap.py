from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.session import Session
from app.models.roadmap import Roadmap
from app.middleware.auth_middleware import get_current_user
from app.schemas.roadmap import RoadmapResponse, SkillAreaSchema, TopicSchema, CourseSchema, SessionRoadmapResponse

router = APIRouter(prefix="/api/v1/roadmap", tags=["Roadmap"])


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
