from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Resolve .env relative to this file so the app loads correctly
# regardless of which directory uvicorn is launched from
_ENV_FILE = str(Path(__file__).parent.parent / ".env")


class Settings(BaseSettings):
    # App
    app_name: str = "Itera"
    debug: bool = False
    secret_key: str

    # Database
    database_url: str

    # CORS: comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost,http://localhost:80,http://localhost:5173"

    # Admin: comma-separated emails allowed to use /api/v3/admin/* endpoints.
    # Empty means admin endpoints are disabled for everyone.
    admin_emails: str = ""

    # ChromaDB persistence directory (mounted as a volume in Docker)
    chroma_path: str = "./chroma_data"

    # Which LLM provider to try first: "groq" or "ollama". The other is the fallback.
    # Groq is skipped when GROQ_API_KEY is empty.
    llm_primary: str = "groq"

    # Ollama (local LLM)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"

    # Groq (hosted LLM). Groq retires models regularly; override via GROQ_MODEL.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    # Groq's free tier has a low tokens-per-minute limit. The OpenAI SDK retries
    # 429s using Groq's retry-after header; this sets how many times.
    groq_max_retries: int = 8

    # Max concurrent LLM calls when generating a roadmap's knowledge base.
    # Keep this low on Groq's free tier to stay under its rate limit.
    kb_concurrency: int = 1

    # YouTube
    youtube_api_key: str = ""

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    @property
    def llm_provider_order(self) -> list[str]:
        """Providers to try, in order. Groq is left out when no API key is set."""
        primary = self.llm_primary.strip().lower()
        order = ["ollama", "groq"] if primary == "ollama" else ["groq", "ollama"]
        if not self.groq_api_key:
            order.remove("groq")
        return order

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    class Config:
        env_file = _ENV_FILE
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()