from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Manifest, Hypothesis
from ..schemas.dto import ManifestCreate, ManifestOut, ManifestLock

router = APIRouter(prefix="/api/manifests", tags=["manifests"])


@router.get("", response_model=list[ManifestOut])
def list_manifests(session: Session = Depends(get_session)):
    rows = session.exec(select(Manifest).order_by(Manifest.created_at.desc())).all()
    return rows


@router.get("/{manifest_id}", response_model=ManifestOut)
def get_manifest(manifest_id: UUID, session: Session = Depends(get_session)):
    m = session.get(Manifest, manifest_id)
    if not m:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return m


@router.post("", response_model=ManifestOut)
def create_manifest(payload: ManifestCreate, session: Session = Depends(get_session)):
    hyp = session.get(Hypothesis, payload.hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=400, detail="Invalid hypothesis_id")

    m = Manifest(hypothesis_id=payload.hypothesis_id, name=payload.name, manifest_json=payload.manifest_json)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


@router.post("/{manifest_id}/lock", response_model=ManifestOut)
def lock_manifest(manifest_id: UUID, payload: ManifestLock, session: Session = Depends(get_session)):
    m = session.get(Manifest, manifest_id)
    if not m:
        raise HTTPException(status_code=404, detail="Manifest not found")
    if m.locked:
        return m
    m.locked = True
    m.lock_reason = payload.reason
    m.locked_at = datetime.utcnow()
    m.locked_by = payload.locked_by
    session.add(m)
    session.commit()
    session.refresh(m)
    return m
