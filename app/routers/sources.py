from __future__ import annotations

import os
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Source
from ..schemas.dto import SourceOut
from ..services import storage

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(session: Session = Depends(get_session)):
    rows = session.exec(select(Source).order_by(Source.created_at.desc())).all()
    return rows


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: UUID, session: Session = Depends(get_session)):
    src = session.get(Source, source_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    return src


@router.post("/upload", response_model=SourceOut)
async def upload_source(file: UploadFile = File(...), session: Session = Depends(get_session)):
    storage.ensure_dirs()
    dest_dir = storage.sources_dir()
    dest_path = os.path.join(dest_dir, file.filename)

    base, ext = os.path.splitext(dest_path)
    i = 1
    while os.path.exists(dest_path):
        dest_path = f"{base}_{i}{ext}"
        i += 1

    async with aiofiles.open(dest_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    src = Source(filename=os.path.basename(dest_path), content_type=file.content_type or "application/octet-stream", path=dest_path)
    session.add(src)
    session.commit()
    session.refresh(src)
    return src
