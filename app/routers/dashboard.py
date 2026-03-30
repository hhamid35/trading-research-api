from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select

from ..db import get_session
from ..models import (
    ExperimentManifest,
    HypothesisCard,
    LiveInstance,
    Run,
    Source,
    StrategyPackage,
)
from ..schemas.research import DashboardStatsOut, RunOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsOut)
def get_stats(session: Session = Depends(get_session)) -> dict:
    sources_count = session.exec(select(func.count(Source.id))).one()
    hypotheses_count = session.exec(select(func.count(HypothesisCard.id))).one()
    manifests_count = session.exec(select(func.count(ExperimentManifest.id))).one()
    runs_count = session.exec(select(func.count(Run.id))).one()
    strategies_count = session.exec(select(func.count(StrategyPackage.id))).one()
    live_instances_count = session.exec(
        select(func.count(LiveInstance.id)).where(
            LiveInstance.status.in_(["STARTING", "RUNNING"])
        )
    ).one()

    recent_runs = list(
        session.exec(select(Run).order_by(Run.started_at.desc()).limit(10)).all()
    )

    return {
        "sources_count": sources_count,
        "hypotheses_count": hypotheses_count,
        "manifests_count": manifests_count,
        "runs_count": runs_count,
        "strategies_count": strategies_count,
        "live_instances_count": live_instances_count,
        "recent_runs": recent_runs,
    }
