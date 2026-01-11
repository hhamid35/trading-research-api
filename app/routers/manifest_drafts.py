from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..models import ManifestDraft
from ..schemas.research import ManifestDraftCreate, ManifestDraftOut
from ..workflows.manifest_graph import (
    create_manifest_draft,
    lock_manifest_draft,
    validate_manifest_draft,
)

router = APIRouter(prefix="/api/manifest_drafts", tags=["manifest_drafts"])


@router.post("", response_model=ManifestDraftOut)
def create_draft(payload: ManifestDraftCreate):
    return create_manifest_draft(payload.hypothesis_id)


@router.get("/{draft_id}", response_model=ManifestDraftOut)
def get_draft(draft_id: UUID, session: Session = Depends(get_session)):
    draft = session.get(ManifestDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/{draft_id}/validate", response_model=ManifestDraftOut)
def validate_draft(draft_id: UUID):
    return validate_manifest_draft(draft_id)


@router.post("/{draft_id}/lock")
def lock_draft(draft_id: UUID):
    manifest = lock_manifest_draft(draft_id)
    return {"manifest_id": str(manifest.id), "locked": manifest.locked}
