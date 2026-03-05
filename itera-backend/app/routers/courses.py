from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.services.course_service import search_courses
from app.schemas.course import CourseSearchResponse, Course

router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])


@router.get("/search", response_model=CourseSearchResponse)
async def search_courses_endpoint(
    query: str = Query(..., description="Topic or skill to search courses for"),
    level: Optional[str] = Query(None, description="Beginner, Intermediate, or Advanced"),
    max_results: Optional[int] = Query(5, description="Number of courses to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Search for courses on any topic using AI.
    Returns real course recommendations from Coursera, Udemy, freeCodeCamp, YouTube and more.
    """
    courses = await search_courses(
        query=query,
        level=level,
        max_results=max_results
    )

    return CourseSearchResponse(
        query=query,
        level=level,
        courses=[Course(**c) for c in courses]
    )