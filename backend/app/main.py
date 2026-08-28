"""BugSense AI - FastAPI Main Application Entrypoint."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes_agentic import router as agentic_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_auth import router as auth_router
from app.api.routes_bugs import router as bugs_router
from app.api.routes_fixes import router as fixes_router
from app.api.routes_health import router as health_router
from app.api.routes_reports import router as reports_router
from app.api.routes_upload import router as upload_router
from app.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging_config import setup_logging
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan context."""
    settings = get_settings()
    setup_logging(debug=settings.DEBUG)
    # Ensure tables exist (Alembic or direct metadata for sqlite dev)
    Base.metadata.create_all(bind=engine)

    # Auto-seed initial demo user & sample bug data on first boot
    try:
        from app.seed_demo import seed
        await seed()
    except Exception as e:
        import logging
        logging.getLogger("bugsense").warning("Startup database seed skipped: %s", str(e))

    yield


def create_app() -> FastAPI:
    """Factory function for FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="LLM-Based Automated  Code Debugging, AST Analysis, and Autonomous Patching Assistant",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Register custom error handling envelopes
    register_error_handlers(app)

    # CORS Configuration
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers under /api
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    app.include_router(bugs_router, prefix="/api")
    app.include_router(fixes_router, prefix="/api")
    app.include_router(agentic_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")

    # Static assets for reports if needed
    storage_dir = os.path.join(os.path.dirname(__file__), "storage")
    os.makedirs(storage_dir, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")

    # Serve Frontend UI directly on root
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    if os.path.exists(frontend_dir):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()
