from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from ..db import get_session, engine
from ..models import LiveInstance, Strategy
from ..schemas.dto import LiveStart, LiveInstanceOut
from ..services.live_runner import simulate_live
from ..ws.hub import hub

router = APIRouter(prefix="/api/live", tags=["live"])


@router.get("", response_model=list[LiveInstanceOut])
def list_live(session: Session = Depends(get_session)):
    rows = session.exec(select(LiveInstance).order_by(LiveInstance.created_at.desc())).all()
    return rows


@router.get("/{instance_id}", response_model=LiveInstanceOut)
def get_live(instance_id: UUID, session: Session = Depends(get_session)):
    inst = session.get(LiveInstance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return inst


@router.post("/start", response_model=LiveInstanceOut)
async def start_live(payload: LiveStart, session: Session = Depends(get_session)):
    strat = session.get(Strategy, payload.strategy_id)
    if not strat:
        raise HTTPException(status_code=400, detail="Invalid strategy_id")

    if payload.mode == "SHADOW" and strat.readiness not in ("APPROVED_FOR_SHADOW", "APPROVED_FOR_PAPER", "APPROVED_FOR_LIVE"):
        raise HTTPException(status_code=400, detail="Strategy not approved for shadow")
    if payload.mode == "PAPER" and strat.readiness not in ("APPROVED_FOR_PAPER", "APPROVED_FOR_LIVE"):
        raise HTTPException(status_code=400, detail="Strategy not approved for paper")

    inst = LiveInstance(strategy_id=strat.id, mode=payload.mode, status="STARTING")
    session.add(inst)
    session.commit()
    session.refresh(inst)

    asyncio.create_task(_live_async(inst.id))
    return inst


async def _live_async(instance_id: UUID) -> None:
    from sqlmodel import Session as S
    with S(engine) as s:
        await simulate_live(s, instance_id)


@router.post("/{instance_id}/stop", response_model=dict)
def stop_live(instance_id: UUID, session: Session = Depends(get_session)):
    inst = session.get(LiveInstance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    inst.status = "STOPPED"
    session.add(inst)
    session.commit()
    return {"ok": True}


@router.websocket("/ws/live/{instance_id}")
async def ws_live(websocket: WebSocket, instance_id: UUID):
    ch = await hub.get(f"live:{instance_id}")
    await ch.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ch.disconnect(websocket)
    except Exception:
        await ch.disconnect(websocket)
