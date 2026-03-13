from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    goal = Column(Text, nullable=False)
    total_estimated_hours = Column(Integer, nullable=False)
    weekly_hours = Column(Integer, nullable=True)
    estimated_weeks = Column(Integer, nullable=True)
    skill_areas = Column(JSONB, nullable=False)  # Full structured roadmap stored as JSON
    completed_topics = Column(JSONB, nullable=True)  # List of completed topic keys
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    session = relationship("Session", back_populates="roadmap")

    def __repr__(self):
        return f"<Roadmap {self.id} goal={self.goal}>"