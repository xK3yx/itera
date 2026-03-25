from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Resolve .env relative to this file so the app loads correctly
# regardless of which directory uvicorn is launched from
_ENV_FILE = str(Path(__file__).parent.parent / ".env")


class Settings(BaseSettings):
    # App
    app_name: str = "Itera"
    debug: bool = True
    secret_key: str

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Ollama (primary LLM)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"

    # Groq (fallback LLM)
    groq_api_key: str = ""

    # YouTube
    youtube_api_key: str = ""

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    class Config:
        env_file = _ENV_FILE
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()