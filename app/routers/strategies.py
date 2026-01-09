from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Strategy, Run
from ..schemas.dto import StrategyCreate, StrategyOut, StrategyApprove

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyOut])
def list_strategies(session: Session = Depends(get_session)):
    rows = session.exec(select(Strategy).order_by(Strategy.created_at.desc())).all()
    return rows


@router.get("/{strategy_id}", response_model=StrategyOut)
def get_strategy(strategy_id: UUID, session: Session = Depends(get_session)):
    s = session.get(Strategy, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@router.post("", response_model=StrategyOut)
def create_strategy(payload: StrategyCreate, session: Session = Depends(get_session)):
    r = session.get(Run, payload.run_id)
    if not r or r.status != "SUCCEEDED":
        raise HTTPException(status_code=400, detail="run_id must refer to a SUCCEEDED run")

    s = Strategy(**payload.model_dump())
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@router.post("/{strategy_id}/approve_shadow", response_model=StrategyOut)
def approve_shadow(strategy_id: UUID, payload: StrategyApprove, session: Session = Depends(get_session)):
    s = session.get(Strategy, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    s.readiness = "APPROVED_FOR_SHADOW"
    s.approved_at = datetime.utcnow()
    s.approved_by = payload.approved_by
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@router.post("/{strategy_id}/approve_paper", response_model=StrategyOut)
def approve_paper(strategy_id: UUID, payload: StrategyApprove, session: Session = Depends(get_session)):
    s = session.get(Strategy, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    s.readiness = "APPROVED_FOR_PAPER"
    s.approved_at = datetime.utcnow()
    s.approved_by = payload.approved_by
    session.add(s)
    session.commit()
    session.refresh(s)
    return s
