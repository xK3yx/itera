from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base
import uuid


class LLMCallLog(Base):
    __tablename__ = "llm_call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_type = Column(String, nullable=False)          # 'roadmap_structure', 'topic_generation', 'kb_generation', 'specificity_check', 'resource_search'
    model_used = Column(String, nullable=False)          # 'qwen2.5:7b' or 'llama-3.3-70b-versatile'
    provider = Column(String, nullable=False)            # 'ollama' or 'groq'
    prompt_messages = Column(JSONB, nullable=False)      # Full messages array sent to LLM
    raw_response = Column(Text, nullable=False)          # Raw text response from LLM
    parsed_successfully = Column(Boolean, nullable=False)
    parse_attempts = Column(Integer, default=1)          # How many retries were needed
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    tokens_total = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    hallucination_flags = Column(JSONB, nullable=True)   # Detected hallucinations
    roadmap_id = Column(UUID(as_uuid=True), nullable=True)
    topic_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
