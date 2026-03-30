from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import HypothesisCard, utcnow
from ..schemas.research import HypothesisCardCreate, HypothesisCardOut

router = APIRouter(prefix="/api/hypotheses", tags=["hypotheses"])


@router.get("/", response_model=list[HypothesisCardOut])
def list_hypotheses(session: Session = Depends(get_session)) -> list[HypothesisCard]:
    return list(
        session.exec(
            select(HypothesisCard).order_by(HypothesisCard.created_at.desc())
        ).all()
    )


@router.get("/{hypothesis_id}", response_model=HypothesisCardOut)
def get_hypothesis(
    hypothesis_id: UUID, session: Session = Depends(get_session)
) -> HypothesisCard:
    h = session.get(HypothesisCard, hypothesis_id)
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return h


@router.post("/", response_model=HypothesisCardOut, status_code=201)
def create_hypothesis(
    payload: HypothesisCardCreate, session: Session = Depends(get_session)
) -> HypothesisCard:
    h = HypothesisCard(
        name=payload.name,
        mechanism=payload.mechanism,
        falsifiable_prediction=payload.falsifiable_prediction,
        null_hypothesis=payload.null_hypothesis,
        decision_timing=payload.decision_timing,
        horizons_ms=payload.horizons_ms,
        primary_metrics=payload.primary_metrics,
        acceptance_criteria=payload.acceptance_criteria,
        tradability_constraints=payload.tradability_constraints,
        failure_modes=payload.failure_modes,
        tags=payload.tags,
    )
    session.add(h)
    session.commit()
    session.refresh(h)
    return h


@router.post("/{hypothesis_id}/approve", response_model=HypothesisCardOut)
def approve_hypothesis(
    hypothesis_id: UUID, session: Session = Depends(get_session)
) -> HypothesisCard:
    h = session.get(HypothesisCard, hypothesis_id)
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    h.status = "APPROVED"
    h.approved_at = utcnow()
    h.approved_by = "local-user"
    session.add(h)
    session.commit()
    session.refresh(h)
    return h
