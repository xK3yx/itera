import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.generated_roadmap import GeneratedRoadmap
from app.services.roadmap_service import generate_roadmap as _generate_roadmap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/roadmaps", tags=["Generated Roadmaps v3"])


class GenerateRoadmapRequest(BaseModel):
    target_role: str = Field(..., min_length=2)
    learning_goal: str = Field(..., min_length=10)
    interests: str | None = None
    hours_per_week: float | None = Field(default=None, ge=1, le=168)
    include_paid: bool = True


def _roadmap_to_dict(rm: GeneratedRoadmap) -> dict:
    return {
        "id": str(rm.id),
        "title": rm.title,
        "description": rm.description,
        "target_role": rm.target_role,
        "learning_goal": rm.learning_goal,
        "interests": rm.interests,
        "hours_per_week": rm.hours_per_week,
        "include_paid": rm.include_paid,
        "total_estimated_hours": rm.total_estimated_hours,
        "roadmap_data": rm.roadmap_data,
        "created_at": rm.created_at.isoformat() if rm.created_at else None,
    }


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_roadmap(
    request: GenerateRoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        logger.info("[Roadmap] Generating for user=%s role=%s", current_user.id, request.target_role)
        rm = await _generate_roadmap(
            db=db,
            user=current_user,
            target_role=request.target_role,
            learning_goal=request.learning_goal,
            interests=request.interests,
            hours_per_week=request.hours_per_week,
            include_paid=request.include_paid,
        )
        return {"data": _roadmap_to_dict(rm)}
    except Exception as exc:
        logger.error("[Roadmap] Generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Roadmap generation failed: {exc}")


@router.get("/")
async def list_roadmaps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedRoadmap)
        .where(GeneratedRoadmap.user_id == current_user.id)
        .order_by(GeneratedRoadmap.created_at.desc())
    )
    roadmaps = result.scalars().all()
    return {"data": [_roadmap_to_dict(rm) for rm in roadmaps]}


@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedRoadmap).where(
            GeneratedRoadmap.id == roadmap_id,
            GeneratedRoadmap.user_id == current_user.id,
        )
    )
    rm = result.scalar_one_or_none()
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return {"data": _roadmap_to_dict(rm)}


@router.delete("/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roadmap(
    roadmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedRoadmap).where(
            GeneratedRoadmap.id == roadmap_id,
            GeneratedRoadmap.user_id == current_user.id,
        )
    )
    rm = result.scalar_one_or_none()
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    await db.delete(rm)
    await db.flush()
