from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select, desc, asc

from ..db import engine
from ..models import ResearchChatSession, ResearchChatMessage
from ..schemas.research import (
    ResearchChatSessionCreate,
    ResearchChatSessionOut,
    ResearchChatMessageCreate,
    ResearchChatMessageOut,
)
from ..research_chat.runtime import run_chat_turn
from ..ws.hub import hub

router = APIRouter(prefix="/api/research_chat", tags=["research_chat"])


@router.post("/sessions", response_model=ResearchChatSessionOut)
def create_session(payload: ResearchChatSessionCreate):
    with Session(engine) as session:
        chat = ResearchChatSession(title=payload.title or "New chat")
        session.add(chat)
        session.commit()
        session.refresh(chat)
        return chat


@router.get("/sessions", response_model=list[ResearchChatSessionOut])
def list_sessions():
    with Session(engine) as session:
        return session.exec(select(ResearchChatSession).order_by(desc(ResearchChatSession.created_at))).all()


@router.get("/sessions/{session_id}", response_model=ResearchChatSessionOut)
def get_session(session_id: UUID):
    with Session(engine) as session:
        chat = session.get(ResearchChatSession, session_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Session not found")
        return chat


@router.get("/sessions/{session_id}/messages", response_model=list[ResearchChatMessageOut])
def list_messages(session_id: UUID):
    with Session(engine) as session:
        return session.exec(
            select(ResearchChatMessage)
            .where(ResearchChatMessage.session_id == session_id)
            .order_by(asc(ResearchChatMessage.created_at))
        ).all()


@router.post("/sessions/{session_id}/messages", response_model=ResearchChatMessageOut)
async def create_message(session_id: UUID, payload: ResearchChatMessageCreate):
    with Session(engine) as session:
        chat = session.get(ResearchChatSession, session_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Session not found")

        msg = ResearchChatMessage(session_id=session_id, role="user", content=payload.content)
        session.add(msg)
        session.commit()
        session.refresh(msg)

    ch = await hub.get(f"research:{session_id}")
    await ch.publish(jsonable_encoder({"type": "message_created", "message": msg.model_dump()}))
    asyncio.create_task(run_chat_turn(session_id, msg.id, lambda data: asyncio.create_task(ch.publish(jsonable_encoder(data)))))
    return msg


@router.websocket("/ws/sessions/{session_id}")
async def ws_session(websocket: WebSocket, session_id: UUID):
    ch = await hub.get(f"research:{session_id}")
    await ch.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ch.disconnect(websocket)
    except Exception:
        await ch.disconnect(websocket)
