"""Health and system status router."""
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/")
async def api_root():
    """API root - lists available endpoints."""
    settings = get_settings()
    return {
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "auth": "/api/auth",
            "upload": "/api/upload",
            "analysis": "/api/analysis",
            "bugs": "/api/bugs",
            "fixes": "/api/fixes",
            "agentic": "/api/agentic",
            "reports": "/api/reports",
        },
        "docs": "/docs",
    }


@router.get("/health")
async def health_check():
    """Service health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "version": "1.0.0",
    }
