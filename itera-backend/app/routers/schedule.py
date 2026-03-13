from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timedelta
import uuid as uuid_lib

from app.database import get_db
from app.models.user import User
from app.models.session import Session
from app.models.roadmap import Roadmap
from app.models.study_schedule import StudySchedule
from app.middleware.auth_middleware import get_current_user
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/v1/schedule", tags=["Schedule"])

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class GenerateScheduleRequest(BaseModel):
    session_id: UUID
    daily_hours: float
    study_days: List[str]


class ScheduleResponse(BaseModel):
    id: UUID
    session_id: UUID
    daily_hours: float
    study_days: List
    schedule: List
    start_date: date
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def _get_study_day_number(start_date: date, study_days: list, target_date: date):
    """
    Return the 1-indexed study day number for target_date.
    Returns None if target_date is before start_date or is not a study day.
    """
    study_day_nums = {DAYS_OF_WEEK.index(d) for d in study_days if d in DAYS_OF_WEEK}

    if target_date < start_date:
        return None
    if target_date.weekday() not in study_day_nums:
        return None

    count = 0
    current = start_date
    while current <= target_date:
        if current.weekday() in study_day_nums:
            count += 1
        current += timedelta(days=1)

    return count


@router.post("/generate", response_model=ScheduleResponse)
async def generate_schedule(
    request: GenerateScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a day-by-day study schedule from a roadmap."""
    # Verify session ownership
    session_result = await db.execute(
        select(Session).where(
            Session.id == request.session_id,
            Session.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Get roadmap
    roadmap_result = await db.execute(
        select(Roadmap).where(Roadmap.session_id == request.session_id)
    )
    roadmap = roadmap_result.scalar_one_or_none()
    if not roadmap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found for this session")

    # Build roadmap dict for AI
    roadmap_dict = {
        "goal": roadmap.goal,
        "total_estimated_hours": roadmap.total_estimated_hours,
        "weekly_hours": roadmap.weekly_hours,
        "skill_areas": roadmap.skill_areas,
    }

    # Generate schedule via AI
    result = await ai_service.generate_study_schedule(
        roadmap=roadmap_dict,
        daily_hours=request.daily_hours,
        study_days=request.study_days,
    )

    today = date.today()

    # Upsert: update existing schedule or create new one
    existing_result = await db.execute(
        select(StudySchedule).where(StudySchedule.session_id == request.session_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.daily_hours = request.daily_hours
        existing.study_days = request.study_days
        existing.schedule = result.get("schedule", [])
        existing.start_date = today
        existing.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        new_schedule = StudySchedule(
            id=uuid_lib.uuid4(),
            session_id=request.session_id,
            daily_hours=request.daily_hours,
            study_days=request.study_days,
            schedule=result.get("schedule", []),
            start_date=today,
        )
        db.add(new_schedule)
        await db.commit()
        await db.refresh(new_schedule)
        return new_schedule


@router.get("/{session_id}", response_model=ScheduleResponse)
async def get_schedule(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the existing study schedule for a session."""
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    schedule_result = await db.execute(
        select(StudySchedule).where(StudySchedule.session_id == session_id)
    )
    schedule = schedule_result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No schedule found for this session")

    return schedule


@router.get("/{session_id}/today")
async def get_today_plan(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get today's study plan from the schedule."""
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    schedule_result = await db.execute(
        select(StudySchedule).where(StudySchedule.session_id == session_id)
    )
    schedule = schedule_result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No schedule found")

    today = date.today()
    day_number = _get_study_day_number(schedule.start_date, schedule.study_days, today)

    if day_number is None:
        # Find next study day
        study_day_nums = {DAYS_OF_WEEK.index(d) for d in schedule.study_days if d in DAYS_OF_WEEK}
        next_day = today + timedelta(days=1)
        for _ in range(7):
            if next_day.weekday() in study_day_nums:
                break
            next_day += timedelta(days=1)

        return {
            "is_study_day": False,
            "next_study_day": DAYS_OF_WEEK[next_day.weekday()],
            "day_number": None,
            "plan": None,
        }

    # Find the matching day entry
    plan_entry = next(
        (entry for entry in schedule.schedule if entry.get("day_number") == day_number),
        None,
    )

    return {
        "is_study_day": True,
        "day_number": day_number,
        "plan": plan_entry,
    }
