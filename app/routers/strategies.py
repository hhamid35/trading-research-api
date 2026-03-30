from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import StrategyPackage
from ..schemas.research import StrategyPackageCreate, StrategyPackageOut

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/", response_model=list[StrategyPackageOut])
def list_strategies(
    session: Session = Depends(get_session),
) -> list[StrategyPackage]:
    return list(
        session.exec(
            select(StrategyPackage).order_by(StrategyPackage.created_at.desc())
        ).all()
    )


@router.get("/{strategy_id}", response_model=StrategyPackageOut)
def get_strategy(
    strategy_id: UUID, session: Session = Depends(get_session)
) -> StrategyPackage:
    s = session.get(StrategyPackage, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@router.post("/", response_model=StrategyPackageOut, status_code=201)
def create_strategy(
    payload: StrategyPackageCreate, session: Session = Depends(get_session)
) -> StrategyPackage:
    s = StrategyPackage(
        name=payload.name,
        run_id=payload.run_id,
        manifest_id=payload.manifest_id,
        hypothesis_id=payload.hypothesis_id,
        version=payload.version,
        parameters=payload.parameters,
        monitoring_spec=payload.monitoring_spec,
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    return s
