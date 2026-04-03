from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB
from sqlalchemy.sql import func
from app.database import Base
import uuid


class RoadmapEnrollment(Base):
    __tablename__ = "roadmap_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    roadmap_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    completed_topic_ids = Column(JSON, default=list)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())


class TopicProgressLog(Base):
    __tablename__ = "topic_progress_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    topic_id = Column(String, nullable=False)
    log_text = Column(Text, nullable=False)
    passed = Column(Boolean, nullable=False)
    rejection_reason = Column(String, nullable=True)
    match_details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
