from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from ..db import get_session
from ..models import Run, RunArtifact
from ..schemas.research import RunCreate, RunOut, RunArtifactOut
from ..utils.logging import get_logger
from ..ws.hub import hub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/", response_model=list[RunOut])
def list_runs(session: Session = Depends(get_session)) -> list[Run]:
    return list(session.exec(select(Run).order_by(Run.started_at.desc())).all())


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: UUID, session: Session = Depends(get_session)) -> Run:
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/", response_model=RunOut, status_code=201)
def create_run(payload: RunCreate, session: Session = Depends(get_session)) -> Run:
    run = Run(
        manifest_id=payload.manifest_id,
        hypothesis_id=payload.hypothesis_id,
        status="QUEUED",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


@router.get("/{run_id}/artifacts", response_model=list[RunArtifactOut])
def list_run_artifacts(
    run_id: UUID, session: Session = Depends(get_session)
) -> list[RunArtifact]:
    return list(
        session.exec(
            select(RunArtifact)
            .where(RunArtifact.run_id == run_id)
            .order_by(RunArtifact.created_at.desc())
        ).all()
    )


@router.websocket("/ws/{run_id}")
async def ws_run(websocket: WebSocket, run_id: UUID) -> None:
    channel = await hub.get(f"run:{run_id}")
    await channel.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for run %s", run_id)
    except Exception as e:
        logger.error("WebSocket error for run %s: %s", run_id, e)
    finally:
        await channel.disconnect(websocket)
