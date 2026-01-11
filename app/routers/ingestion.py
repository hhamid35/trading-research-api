from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from ..db import get_session
from ..models import IngestionJob
from ..schemas.research import IngestionJobCreate, IngestionJobOut
from ..utils.logging import get_logger
from ..workflows.ingestion_graph import run_ingestion_job
from ..ws.hub import hub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


def _get_channel_key(job_id: UUID) -> str:
    """Format channel key for ingestion job."""
    return f"ingestion:{job_id}"


@router.post("/jobs", response_model=IngestionJobOut)
async def create_job(
    payload: IngestionJobCreate, session: Session = Depends(get_session)
) -> IngestionJob:
    """Create a new ingestion job and start processing.

    This endpoint:
    1. Persists the ingestion job
    2. Publishes initial status via WebSocket
    3. Triggers async job execution
    """
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

    # Publish initial status and trigger job execution
    channel = await hub.get(_get_channel_key(job.id))
    await channel.publish(
        jsonable_encoder(
            {"type": "status", "status": job.status, "job_id": str(job.id)}
        )
    )

    def publish_event(data: dict[str, Any]) -> None:
        """Synchronous wrapper that schedules async channel publish."""
        asyncio.create_task(channel.publish(jsonable_encoder(data)))

    asyncio.create_task(run_ingestion_job(job.id, publish=publish_event))
    return job


@router.get("/jobs/{job_id}", response_model=IngestionJobOut)
def get_job(job_id: UUID, session: Session = Depends(get_session)) -> IngestionJob:
    """Get a specific ingestion job by ID."""
    job = session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/retry", response_model=IngestionJobOut)
async def retry_job(
    job_id: UUID, session: Session = Depends(get_session)
) -> IngestionJob:
    """Retry a failed ingestion job.

    Resets the job status to QUEUED and triggers execution.
    """
    job = session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.attempts += 1
    job.status = "QUEUED"
    job.last_error = None
    session.add(job)
    session.commit()
    session.refresh(job)

    # Publish status update and trigger job execution
    channel = await hub.get(_get_channel_key(job.id))
    await channel.publish(
        jsonable_encoder(
            {"type": "status", "status": job.status, "job_id": str(job.id)}
        )
    )

    def publish_event(data: dict[str, Any]) -> None:
        """Synchronous wrapper that schedules async channel publish."""
        asyncio.create_task(channel.publish(jsonable_encoder(data)))

    asyncio.create_task(run_ingestion_job(job.id, publish=publish_event))
    return job


@router.websocket("/ws/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: UUID) -> None:
    """WebSocket endpoint for receiving real-time ingestion job updates.

    Clients connect to receive status events, progress updates, and error messages.
    """
    channel = await hub.get(_get_channel_key(job_id))
    await channel.connect(websocket)

    try:
        # Keep connection alive and handle client-initiated closure
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for job %s", job_id)
    except Exception as e:
        logger.error("WebSocket error for job %s: %s", job_id, e)
    finally:
        await channel.disconnect(websocket)
