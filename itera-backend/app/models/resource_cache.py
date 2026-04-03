from sqlalchemy import Column, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class ResourceCache(Base):
    """Cached resources per search query — shared across all users and roadmaps."""
    __tablename__ = "resource_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_query = Column(Text, unique=True, nullable=False, index=True)
    # Stores ALL resources (free + paid). Filter at read time based on include_paid.
    resources = Column(JSONB, nullable=False)
    hit_count = Column(Integer, server_default="0", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
