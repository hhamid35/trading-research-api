from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .services import storage
from .routers import providers, sources, hypotheses, manifests, patches, runs, strategies, live


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
        storage.ensure_dirs()
        init_db()

    app.include_router(providers.router)
    app.include_router(sources.router)
    app.include_router(hypotheses.router)
    app.include_router(manifests.router)
    app.include_router(patches.router)
    app.include_router(runs.router)
    app.include_router(strategies.router)
    app.include_router(live.router)

    @app.get("/health")
    def health():
        return {"ok": True, "env": settings.environment}

    return app


app = create_app()
