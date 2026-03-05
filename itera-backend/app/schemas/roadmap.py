from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class CourseSchema(BaseModel):
    title: str
    platform: str
    url: str
    duration: str
    level: str
    why_recommended: Optional[str] = None


class TopicSchema(BaseModel):
    name: str
    estimated_hours: int
    description: str
    why_relevant: Optional[str] = None
    courses: list[CourseSchema] = []


class SkillAreaSchema(BaseModel):
    name: str
    description: str
    estimated_hours: int
    topics: list[TopicSchema] = []


class RoadmapResponse(BaseModel):
    roadmap_id: UUID
    session_id: UUID
    goal: str
    total_estimated_hours: int
    weekly_hours: Optional[int] = None
    estimated_weeks: Optional[int] = None
    skill_areas: list[SkillAreaSchema]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionRoadmapResponse(BaseModel):
    session_id: UUID
    session_title: str
    status: str
    roadmap: Optional[RoadmapResponse] = None