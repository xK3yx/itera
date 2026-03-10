from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class StartSessionRequest(BaseModel):
    title: Optional[str] = "New Learning Session"


class StartSessionResponse(BaseModel):
    session_id: UUID
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageResponse(BaseModel):
    session_id: UUID
    ready: bool
    message: str
    roadmap: Optional[dict] = None


class SessionHistoryResponse(BaseModel):
    session_id: UUID
    title: Optional[str] = None
    goal: Optional[str] = None
    status: str
    created_at: datetime
    messages: list[MessageResponse]

    class Config:
        from_attributes = True