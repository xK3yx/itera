from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/v1/explain", tags=["Explain"])


class TopicExplainRequest(BaseModel):
    topic_name: str
    topic_description: Optional[str] = ""
    why_relevant: Optional[str] = ""
    goal: str


class TopicExplainResponse(BaseModel):
    explanation: str


@router.post("/topic", response_model=TopicExplainResponse)
async def explain_topic(
    request: TopicExplainRequest,
    current_user: User = Depends(get_current_user)
):
    """Get a beginner-friendly AI explanation of any roadmap topic."""
    explanation = await ai_service.explain_topic(
        topic_name=request.topic_name,
        topic_description=request.topic_description or "",
        why_relevant=request.why_relevant or "",
        goal=request.goal
    )
    return TopicExplainResponse(explanation=explanation)
