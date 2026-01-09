from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Hypothesis
from ..schemas.dto import HypothesisCreate, HypothesisOut, HypothesisApprove

router = APIRouter(prefix="/api/hypotheses", tags=["hypotheses"])


@router.get("", response_model=list[HypothesisOut])
def list_hypotheses(session: Session = Depends(get_session)):
    rows = session.exec(select(Hypothesis).order_by(Hypothesis.created_at.desc())).all()
    return rows


@router.get("/{hypothesis_id}", response_model=HypothesisOut)
def get_hypothesis(hypothesis_id: UUID, session: Session = Depends(get_session)):
    h = session.get(Hypothesis, hypothesis_id)
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return h


@router.post("", response_model=HypothesisOut)
def create_hypothesis(payload: HypothesisCreate, session: Session = Depends(get_session)):
    h = Hypothesis(**payload.model_dump())
    session.add(h)
    session.commit()
    session.refresh(h)
    return h


@router.post("/{hypothesis_id}/approve", response_model=HypothesisOut)
def approve_hypothesis(hypothesis_id: UUID, payload: HypothesisApprove, session: Session = Depends(get_session)):
    h = session.get(Hypothesis, hypothesis_id)
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    h.status = "APPROVED"
    h.approved_at = datetime.utcnow()
    h.approved_by = payload.approved_by
    session.add(h)
    session.commit()
    session.refresh(h)
    return h
