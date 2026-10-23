import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.projects import router as projects_router

app = FastAPI(
    title="TaskFlow API",
    description="TaskFlow backend API",
    version="0.1.0",
)

# CORS configuration
allowed_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])


@app.get("/")
def root():
    """Root endpoint welcoming users to TaskFlow."""
    return {"message": "Welcome to TaskFlow"}


@app.get("/health")
def health_check():
    """Health check endpoint to verify backend service availability."""
    return {
        "status": "ok",
        "service": "TaskFlow API",
        "version": "0.1.0",
    }