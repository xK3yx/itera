from sqlalchemy import Column, Float, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class StudySchedule(Base):
    __tablename__ = "study_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    daily_hours = Column(Float, nullable=False)
    study_days = Column(JSONB, nullable=False)   # e.g. ["Monday", "Wednesday", "Friday"]
    schedule = Column(JSONB, nullable=False)      # AI-generated day-by-day plan
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<StudySchedule session={self.session_id}>"
