from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth, generated_roadmaps, users, roadmap_progress
from app.routers import knowledge_base, admin

APP_VERSION = "3.2.0"

settings = get_settings()

app = FastAPI(
    title="Itera API",
    description="Personalized AI learning roadmap generator",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(generated_roadmaps.router)
app.include_router(users.router)
app.include_router(roadmap_progress.router)
app.include_router(knowledge_base.router)
app.include_router(admin.router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": APP_VERSION
    }


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name} API v{APP_VERSION}"}
