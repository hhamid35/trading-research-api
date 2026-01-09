from __future__ import annotations

import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import CodePatch
from ..schemas.dto import CodePatchCreate, CodePatchOut, CodePatchApply
from ..services import storage

router = APIRouter(prefix="/api/code_patches", tags=["code_patches"])


@router.get("", response_model=list[CodePatchOut])
def list_patches(session: Session = Depends(get_session)):
    rows = session.exec(select(CodePatch).order_by(CodePatch.created_at.desc())).all()
    return rows


@router.post("", response_model=CodePatchOut)
def create_patch(payload: CodePatchCreate, session: Session = Depends(get_session)):
    storage.ensure_dirs()
    p = CodePatch(**payload.model_dump())
    session.add(p)
    session.commit()
    session.refresh(p)

    patch_dir = storage.patches_dir()
    patch_path = os.path.join(patch_dir, f"{p.id}.patch.txt")
    with open(patch_path, "w", encoding="utf-8") as f:
        f.write(p.content)
    return p


@router.post("/{patch_id}/apply", response_model=dict)
def apply_patch(patch_id: UUID, payload: CodePatchApply, session: Session = Depends(get_session)):
    p = session.get(CodePatch, patch_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patch not found")
    if p.status != "PROPOSED":
        raise HTTPException(status_code=400, detail=f"Cannot apply patch in status {p.status}")

    rel_path = p.path.lstrip("/").replace("..", "")
    abs_path = os.path.abspath(rel_path)

    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(p.content)

    p.status = "APPLIED"
    p.applied_at = datetime.utcnow()
    p.applied_by = payload.approved_by
    session.add(p)
    session.commit()

    return {"ok": True, "applied_to": abs_path}
