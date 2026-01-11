"""Trading Research API - Main application module."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .db import create_db_and_tables
from .routers import (
    health,
    hypothesis_drafts,
    ingestion,
    manifest_drafts,
    research_chat,
    search,
)
from .services.storage import ensure_dirs
from .utils.logging import get_logger, log_request, setup_logging


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: ARG001
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize storage directories and database tables
    - Shutdown: Clean up resources

    Args:
        application: FastAPI instance (required by framework but unused in context)
    """
    settings = get_settings()
    logger = get_logger(__name__)
    logger.info(
        "Application starting up",
        extra={
            "app_name": settings.app_name,
            "environment": settings.environment,
            "debug": settings.debug,
        },
    )

    # Initialize application resources
    ensure_dirs()
    create_db_and_tables()

    yield

    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    # Configure structured logging with loguru
    json_format = settings.environment in ["staging", "prod"]
    setup_logging(log_level=str(settings.log_level), json_format=json_format)

    logger = get_logger(__name__)

    # Create FastAPI application
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Trading Research Platform API - "
            "Local-first agentic research and experiment runner"
        ),
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            o.strip() for o in str(settings.cors_allow_origins).split(",") if o.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request logging middleware
    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests with timing information."""
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Use structured logging utility
        log_request(
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response

    # Global exception handler
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors."""
        logger.error(
            "Unhandled exception occurred",
            extra={
                "method": request.method,
                "path": str(request.url.path),
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )

        # Don't expose internal errors in production
        if settings.debug:
            detail = f"Internal server error: {str(exc)}"
        else:
            detail = "Internal server error"

        return JSONResponse(
            status_code=500,
            content={
                "detail": detail,
                "type": "internal_server_error",
            },
        )

    # HTTP exception handler
    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent formatting."""
        logger.warning(
            "HTTP exception occurred",
            extra={
                "method": request.method,
                "path": str(request.url.path),
                "status_code": exc.status_code,
                "detail": exc.detail,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "type": "http_exception",
                "status_code": exc.status_code,
            },
        )

    # Include routers
    application.include_router(health.router)
    application.include_router(research_chat.router)
    application.include_router(ingestion.router)
    application.include_router(search.router)
    application.include_router(hypothesis_drafts.router)
    application.include_router(manifest_drafts.router)

    # Root endpoint
    @application.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "status": "running",
            "environment": settings.environment,
            "timestamp": time.time(),
            "endpoints": {
                "health": "/health/",
                "research_chat": "/api/research_chat/",
                "ingestion": "/api/ingestion/",
                "search": "/api/search/",
                "hypotheses": "/api/hypothesis_drafts/",
                "manifests": "/api/manifest_drafts/",
                "docs": "/docs",
                "redoc": "/redoc",
            },
        }

    logger.info("FastAPI application created successfully")
    return application


# Create application instance
app = create_app()

if __name__ == "__main__":
    """Run the application directly."""
    settings = get_settings()

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,
        access_log=False,
    )
