from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..schemas.research import ProviderOut

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/", response_model=list[ProviderOut])
def list_providers() -> list[dict]:
    settings = get_settings()
    providers = [
        {
            "name": settings.llm_provider,
            "kind": "llm",
            "status": "configured" if settings.openai_api_key.get_secret_value() else "unconfigured",
            "base_url": "",
            "capabilities": {"model": settings.llm_openai_model},
        },
        {
            "name": settings.vector_db_provider,
            "kind": "vectordb",
            "status": "configured",
            "base_url": settings.qdrant_url,
            "capabilities": {"collection": settings.qdrant_collection},
        },
        {
            "name": settings.search_provider,
            "kind": "search",
            "status": "configured",
            "base_url": settings.searxng_url,
            "capabilities": {},
        },
    ]
    return providers
