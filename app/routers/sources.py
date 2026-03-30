from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from ..db import get_session
from ..models import Source
from ..schemas.research import SourceCreate, SourceOut
from ..services.storage import ensure_dirs
from ..config import get_settings

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("/", response_model=list[SourceOut])
def list_sources(session: Session = Depends(get_session)) -> list[Source]:
    return list(session.exec(select(Source).order_by(Source.created_at.desc())).all())


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: UUID, session: Session = Depends(get_session)) -> Source:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/", response_model=SourceOut, status_code=201)
def create_source(
    payload: SourceCreate, session: Session = Depends(get_session)
) -> Source:
    source = Source(
        kind=payload.kind,
        title=payload.title,
        filename=payload.filename,
        uri=payload.uri,
        content_type=payload.content_type,
        notes=payload.notes,
        tags=payload.tags,
        metadata_=payload.metadata_,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


@router.post("/upload", response_model=SourceOut, status_code=201)
def upload_source(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> Source:
    settings = get_settings()
    ensure_dirs()

    content = file.file.read()
    sha256 = hashlib.sha256(content).hexdigest()

    import os

    storage_path = os.path.join(settings.storage_dir, "sources", sha256)
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "wb") as f:
        f.write(content)

    source = Source(
        kind="UPLOAD",
        title=file.filename or "Untitled",
        filename=file.filename or "",
        content_type=file.content_type or "application/octet-stream",
        checksum_sha256=sha256,
        bytes=len(content),
        storage_path=storage_path,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source
