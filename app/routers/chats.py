"""Alias router: maps /api/chats/* to the research_chat endpoints for UI compatibility."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, asc, desc, select

from ..db import engine
from ..models import ResearchChatMessage, ResearchChatSession
from ..schemas.research import (
    ResearchChatMessageCreate,
    ResearchChatMessageOut,
    ResearchChatSessionCreate,
    ResearchChatSessionOut,
)
from ..utils.logging import get_logger
from ..ws.hub import hub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("/", response_model=list[ResearchChatSessionOut])
def list_sessions() -> list[ResearchChatSession]:
    with Session(engine) as db:
        return list(
            db.exec(
                select(ResearchChatSession).order_by(
                    desc(ResearchChatSession.created_at)
                )
            ).all()
        )


@router.post("/", response_model=ResearchChatSessionOut, status_code=201)
def create_session(payload: ResearchChatSessionCreate) -> ResearchChatSession:
    with Session(engine) as db:
        chat = ResearchChatSession(title=payload.title or "New chat")
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat


@router.get("/{session_id}", response_model=ResearchChatSessionOut)
def get_session(session_id: UUID) -> ResearchChatSession:
    with Session(engine) as db:
        chat = db.get(ResearchChatSession, session_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Session not found")
        return chat


@router.get(
    "/{session_id}/messages", response_model=list[ResearchChatMessageOut]
)
def list_messages(session_id: UUID) -> list[ResearchChatMessage]:
    with Session(engine) as db:
        return list(
            db.exec(
                select(ResearchChatMessage)
                .where(ResearchChatMessage.session_id == session_id)
                .order_by(asc(ResearchChatMessage.created_at))
            ).all()
        )


@router.post(
    "/{session_id}/messages", response_model=ResearchChatMessageOut
)
def create_message(
    session_id: UUID, payload: ResearchChatMessageCreate
) -> ResearchChatMessage:
    with Session(engine) as db:
        chat = db.get(ResearchChatSession, session_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Session not found")
        msg = ResearchChatMessage(
            session_id=session_id, role="user", content=payload.content
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg


@router.websocket("/ws/{session_id}")
async def ws_session(websocket: WebSocket, session_id: UUID) -> None:
    channel = await hub.get(f"research:{session_id}")
    await channel.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as e:
        logger.error("WebSocket error for session %s: %s", session_id, e)
    finally:
        await channel.disconnect(websocket)
