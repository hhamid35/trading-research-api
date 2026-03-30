from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import ExperimentManifest, utcnow
from ..schemas.research import ExperimentManifestCreate, ExperimentManifestOut

router = APIRouter(prefix="/api/manifests", tags=["manifests"])


@router.get("/", response_model=list[ExperimentManifestOut])
def list_manifests(
    session: Session = Depends(get_session),
) -> list[ExperimentManifest]:
    return list(
        session.exec(
            select(ExperimentManifest).order_by(
                ExperimentManifest.created_at.desc()
            )
        ).all()
    )


@router.get("/{manifest_id}", response_model=ExperimentManifestOut)
def get_manifest(
    manifest_id: UUID, session: Session = Depends(get_session)
) -> ExperimentManifest:
    m = session.get(ExperimentManifest, manifest_id)
    if not m:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return m


@router.post("/", response_model=ExperimentManifestOut, status_code=201)
def create_manifest(
    payload: ExperimentManifestCreate, session: Session = Depends(get_session)
) -> ExperimentManifest:
    m = ExperimentManifest(
        hypothesis_id=payload.hypothesis_id,
        name=payload.name,
        manifest_json=payload.manifest_json,
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


@router.post("/{manifest_id}/lock", response_model=ExperimentManifestOut)
def lock_manifest(
    manifest_id: UUID, session: Session = Depends(get_session)
) -> ExperimentManifest:
    m = session.get(ExperimentManifest, manifest_id)
    if not m:
        raise HTTPException(status_code=404, detail="Manifest not found")
    if m.locked:
        raise HTTPException(status_code=409, detail="Manifest already locked")
    m.locked = True
    m.locked_at = utcnow()
    m.locked_by = "local-user"
    session.add(m)
    session.commit()
    session.refresh(m)
    return m
