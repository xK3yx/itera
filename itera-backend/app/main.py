from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth

settings = get_settings()

app = FastAPI(
    title="Itera API",
    description="Personalized AI learning roadmap generator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name} API"}


@app.get("/test-ai")
async def test_ai():
    """Test Groq API connection."""
    from app.services.ai_service import ai_service
    connected, message = await ai_service.test_connection()
    return {
        "groq_connected": connected,
        "status": "ok" if connected else "error",
        "message": message
    }


@app.get("/test-roadmap")
async def test_roadmap():
    """
    Test full roadmap generation with a sample profile.
    Simulates: 5yr Python/Django backend dev wanting to learn React, 10hrs/week.
    """
    from app.services.ai_service import ai_service
    result = await ai_service.test_roadmap_generation()
    return result