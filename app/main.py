from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .db import create_db_and_tables
from .services.storage import ensure_dirs

from .routers import research_chat, ingestion, search, hypothesis_drafts, manifest_drafts


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_allow_origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        ensure_dirs()
        create_db_and_tables()
        
    app.include_router(research_chat.router)
    app.include_router(ingestion.router)
    app.include_router(search.router)
    app.include_router(hypothesis_drafts.router)
    app.include_router(manifest_drafts.router)
        
    @app.get("/health")
    def health():
        return {"ok": True, "env": settings.environment}

    return app


app = create_app()
