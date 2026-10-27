from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware import RequestIDAndLoggingMiddleware, setup_json_logging
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router

# Initialize structured JSON logging
setup_json_logging(settings.LOG_LEVEL)

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="TaskFlow backend API",
    version="0.1.0",
)

# 1. Request-ID & Structured Logging Middleware
app.add_middleware(RequestIDAndLoggingMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Register API Routers
app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])


@app.get("/")
def root():
    """Root endpoint welcoming users to TaskFlow."""
    return {"message": f"Welcome to {settings.APP_NAME}"}


@app.get("/health")
def health_check():
    """Liveness probe reporting process status and API metadata."""
    return {
        "status": "ok",
        "service": f"{settings.APP_NAME} API",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }


@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe actively checking database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "service": f"{settings.APP_NAME} API",
        }
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "database": "disconnected",
                "detail": f"Database connection failed: {exc}",
            },
        )
