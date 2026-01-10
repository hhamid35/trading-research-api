from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select

from ..db import get_session
from ..models import IngestionJob
from ..schemas.research import IngestionJobCreate, IngestionJobOut
from ..workflows.ingestion_graph import run_ingestion_job
from ..ws.hub import hub

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/jobs", response_model=IngestionJobOut)
async def create_job(payload: IngestionJobCreate, session: Session = Depends(get_session)):
    job = IngestionJob(
        source_id=payload.source_id,
        status="QUEUED",
        attempts=0,
        last_error=None,
        thread_id=f"ingest:{payload.source_id}",
        config_json=payload.config,
        stats_json={},
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    ch = await hub.get(f"ingestion:{job.id}")
    await ch.publish(jsonable_encoder({"type": "status", "status": job.status, "job_id": str(job.id)}))
    asyncio.create_task(run_ingestion_job(job.id, publish=lambda data: asyncio.create_task(ch.publish(jsonable_encoder(data)))))
    return job


@router.get("/jobs/{job_id}", response_model=IngestionJobOut)
def get_job(job_id: UUID, session: Session = Depends(get_session)):
    job = session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/retry", response_model=IngestionJobOut)
async def retry_job(job_id: UUID, session: Session = Depends(get_session)):
    job = session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.attempts += 1
    job.status = "QUEUED"
    job.last_error = None
    session.add(job)
    session.commit()
    session.refresh(job)

    ch = await hub.get(f"ingestion:{job.id}")
    await ch.publish(jsonable_encoder({"type": "status", "status": job.status, "job_id": str(job.id)}))
    asyncio.create_task(run_ingestion_job(job.id, publish=lambda data: asyncio.create_task(ch.publish(jsonable_encoder(data)))))
    return job


@router.websocket("/ws/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: UUID):
    ch = await hub.get(f"ingestion:{job_id}")
    await ch.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ch.disconnect(websocket)
    except Exception:
        await ch.disconnect(websocket)
