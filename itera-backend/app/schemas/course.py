from pydantic import BaseModel
from typing import Optional


class CourseSearchRequest(BaseModel):
    query: str
    level: Optional[str] = None  # Beginner, Intermediate, Advanced
    max_results: Optional[int] = 5


class Course(BaseModel):
    title: str
    platform: str
    url: str
    duration: str
    level: str
    description: str
    why_recommended: str


class CourseSearchResponse(BaseModel):
    query: str
    level: Optional[str] = None
    courses: list[Course]