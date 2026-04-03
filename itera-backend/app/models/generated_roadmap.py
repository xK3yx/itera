from sqlalchemy import Column, String, Boolean, DateTime, Float, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class GeneratedRoadmap(Base):
    __tablename__ = "generated_roadmaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    target_role = Column(String, nullable=False)
    learning_goal = Column(Text, nullable=False)
    interests = Column(Text, nullable=True)
    hours_per_week = Column(Float, nullable=True)
    include_paid = Column(Boolean, default=True)
    total_estimated_hours = Column(Float, default=0)
    roadmap_data = Column(JSON, nullable=False)  # Full structured roadmap
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    data = Column(JSON, nullable=False)  # KB data for all topics
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
