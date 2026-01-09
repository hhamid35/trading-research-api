from __future__ import annotations

from fastapi import APIRouter
from ..schemas.dto import ProviderOut
from ..services.providers import provider_registry

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderOut])
def list_providers():
    out: list[ProviderOut] = []
    for p in provider_registry.list():
        out.append(ProviderOut(name=p.name, status=p.status, capabilities=p.capabilities or {}))
    return out
