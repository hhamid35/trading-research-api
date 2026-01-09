from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from ..models import Run, Manifest
from ..services.storage import run_artifacts_dir
from ..services.util import stable_json_hash
from ..ws.hub import hub


async def simulate_run(session: Session, run_id: UUID) -> None:
    run = session.get(Run, run_id)
    if not run:
        return

    ch = await hub.get(f"runs:{run_id}")

    run.status = "RUNNING"
    run.started_at = datetime.utcnow()
    run.artifacts_dir = run_artifacts_dir(run_id)
    session.add(run)
    session.commit()

    await ch.publish({"ts": datetime.utcnow().isoformat(), "level": "INFO", "msg": "Run started", "progress": 0.01})

    manifest = session.get(Manifest, run.manifest_id)
    manifest_json = manifest.manifest_json if manifest else {}

    run.dataset_hash = stable_json_hash({"dataset": manifest_json.get("dataset", {})})
    run.feature_hash = stable_json_hash({"features": manifest_json.get("features", [])})
    run.label_hash = stable_json_hash({"labels": manifest_json.get("labels", [])})
    run.model_hash = stable_json_hash({"model": manifest_json.get("model", {})})
    run.execution_hash = stable_json_hash({"execution": manifest_json.get("execution", {})})
    session.add(run)
    session.commit()

    stages = [
        ("Building dataset", 0.15),
        ("Reconstructing book state (if needed)", 0.30),
        ("Generating features", 0.45),
        ("Generating labels", 0.55),
        ("Training model / compiling rules", 0.70),
        ("Backtesting policy", 0.85),
        ("Computing robustness slices", 0.93),
    ]
    for msg, prog in stages:
        await asyncio.sleep(0.25)
        await ch.publish({"ts": datetime.utcnow().isoformat(), "level": "INFO", "msg": msg, "progress": prog})

    await asyncio.sleep(0.2)
    run.metrics = {
        "after_cost_expectancy": 0.08,
        "sharpe": 1.10,
        "max_drawdown": -950.0,
        "hit_rate": 0.54,
        "turnover": 120,
    }
    run.warnings = [
        "SIMULATION ONLY: Replace with real pipeline/backtest.",
        "Validate slippage model and walk-forward split logic before trusting results.",
    ]

    run.status = "SUCCEEDED"
    run.ended_at = datetime.utcnow()
    session.add(run)
    session.commit()

    await ch.publish({"ts": datetime.utcnow().isoformat(), "level": "INFO", "msg": "Run completed", "progress": 1.0})
