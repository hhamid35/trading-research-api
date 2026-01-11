from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..models import HypothesisDraft
from ..schemas.research import HypothesisDraftCreate, HypothesisDraftOut
from ..workflows.hypothesis_graph import approve_hypothesis, run_hypothesis_graph

router = APIRouter(prefix="/api/hypothesis_drafts", tags=["hypothesis_drafts"])


@router.post("", response_model=HypothesisDraftOut)
def create_draft(payload: HypothesisDraftCreate):
    return run_hypothesis_graph(payload.session_id)


@router.get("/{draft_id}", response_model=HypothesisDraftOut)
def get_draft(draft_id: UUID, session: Session = Depends(get_session)):
    draft = session.get(HypothesisDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/{draft_id}/approve")
def approve_draft(draft_id: UUID):
    card = approve_hypothesis(draft_id)
    return {"hypothesis_id": str(card.id), "status": card.status}


@router.post("/{draft_id}/reject")
def reject_draft(draft_id: UUID, session: Session = Depends(get_session)):
    draft = session.get(HypothesisDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "REJECTED"
    session.add(draft)
    session.commit()
    return {"status": draft.status}
