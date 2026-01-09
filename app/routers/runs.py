from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from ..db import get_session, engine
from ..models import Run, Manifest
from ..schemas.dto import RunCreate, RunOut
from ..services import storage
from ..services.runner import simulate_run
from ..ws.hub import hub

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[RunOut])
def list_runs(session: Session = Depends(get_session)):
    rows = session.exec(select(Run).order_by(Run.id.desc())).all()
    return rows


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: UUID, session: Session = Depends(get_session)):
    r = session.get(Run, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    return r


@router.post("", response_model=RunOut)
async def create_run(payload: RunCreate, session: Session = Depends(get_session)):
    storage.ensure_dirs()
    m = session.get(Manifest, payload.manifest_id)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid manifest_id")
    if not m.locked:
        raise HTTPException(status_code=400, detail="Manifest must be locked (preregistered) before running")

    r = Run(hypothesis_id=m.hypothesis_id, manifest_id=m.id, artifacts_dir="")
    session.add(r)
    session.commit()
    session.refresh(r)

    asyncio.create_task(_run_async(r.id))
    return r


async def _run_async(run_id: UUID) -> None:
    from sqlmodel import Session as S
    with S(engine) as s:
        await simulate_run(s, run_id)


@router.websocket("/ws/runs/{run_id}")
async def ws_run_logs(websocket: WebSocket, run_id: UUID):
    ch = await hub.get(f"runs:{run_id}")
    await ch.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive
    except WebSocketDisconnect:
        await ch.disconnect(websocket)
    except Exception:
        await ch.disconnect(websocket)
