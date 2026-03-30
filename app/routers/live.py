from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from ..db import get_session
from ..models import LiveInstance, utcnow
from ..schemas.research import LiveInstanceCreate, LiveInstanceOut
from ..utils.logging import get_logger
from ..ws.hub import hub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/live", tags=["live"])


@router.get("/", response_model=list[LiveInstanceOut])
def list_live(session: Session = Depends(get_session)) -> list[LiveInstance]:
    return list(
        session.exec(
            select(LiveInstance).order_by(LiveInstance.created_at.desc())
        ).all()
    )


@router.post("/start", response_model=LiveInstanceOut, status_code=201)
def start_live(
    payload: LiveInstanceCreate, session: Session = Depends(get_session)
) -> LiveInstance:
    instance = LiveInstance(
        strategy_id=payload.strategy_id,
        mode=payload.mode,
        status="STARTING",
    )
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


@router.post("/{instance_id}/stop", response_model=LiveInstanceOut)
def stop_live(
    instance_id: UUID, session: Session = Depends(get_session)
) -> LiveInstance:
    instance = session.get(LiveInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Live instance not found")
    instance.status = "STOPPED"
    instance.stopped_at = utcnow()
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


@router.websocket("/ws/{instance_id}")
async def ws_live(websocket: WebSocket, instance_id: UUID) -> None:
    channel = await hub.get(f"live:{instance_id}")
    await channel.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for live instance %s", instance_id)
    except Exception as e:
        logger.error("WebSocket error for live instance %s: %s", instance_id, e)
    finally:
        await channel.disconnect(websocket)
