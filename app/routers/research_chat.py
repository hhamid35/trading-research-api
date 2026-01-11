from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, asc, desc, select

from ..db import engine
from ..models import ResearchChatMessage, ResearchChatSession
from ..research_chat.runtime import run_chat_turn
from ..schemas.research import (
    ResearchChatMessageCreate,
    ResearchChatMessageOut,
    ResearchChatSessionCreate,
    ResearchChatSessionOut,
)
from ..utils.logging import get_logger
from ..ws.hub import hub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/research_chat", tags=["research_chat"])


def _get_channel_key(session_id: UUID) -> str:
    """Format channel key for research chat session."""
    return f"research:{session_id}"


@router.post("/sessions", response_model=ResearchChatSessionOut)
def create_session(payload: ResearchChatSessionCreate) -> ResearchChatSession:
    """Create a new research chat session."""
    with Session(engine) as db:
        chat = ResearchChatSession(title=payload.title or "New chat")
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat


@router.get("/sessions", response_model=list[ResearchChatSessionOut])
def list_sessions() -> list[ResearchChatSession]:
    """List all research chat sessions, ordered by creation date (newest first)."""
    with Session(engine) as db:
        return list(
            db.exec(
                select(ResearchChatSession).order_by(
                    desc(ResearchChatSession.created_at)
                )
            ).all()
        )


@router.get("/sessions/{session_id}", response_model=ResearchChatSessionOut)
def get_session(session_id: UUID) -> ResearchChatSession:
    """Get a specific research chat session by ID."""
    with Session(engine) as db:
        chat = db.get(ResearchChatSession, session_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Session not found")
        return chat


@router.get(
    "/sessions/{session_id}/messages", response_model=list[ResearchChatMessageOut]
)
def list_messages(session_id: UUID) -> list[ResearchChatMessage]:
    """List all messages in a research chat session, ordered chronologically."""
    with Session(engine) as db:
        return list(
            db.exec(
                select(ResearchChatMessage)
                .where(ResearchChatMessage.session_id == session_id)
                .order_by(asc(ResearchChatMessage.created_at))
            ).all()
        )


@router.post("/sessions/{session_id}/messages", response_model=ResearchChatMessageOut)
async def create_message(
    session_id: UUID, payload: ResearchChatMessageCreate
) -> ResearchChatMessage:
    """Create a new user message and trigger AI response.

    This endpoint:
    1. Persists the user message
    2. Publishes message_created event via WebSocket
    3. Triggers async chat turn execution
    """
    # Persist user message
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

    # Publish message created event and trigger chat turn
    channel = await hub.get(_get_channel_key(session_id))
    await channel.publish(
        jsonable_encoder({"type": "message_created", "message": msg.model_dump()})
    )

    def publish_event(data: dict[str, Any]) -> None:
        """Synchronous wrapper that schedules async channel publish."""
        asyncio.create_task(channel.publish(jsonable_encoder(data)))

    asyncio.create_task(run_chat_turn(session_id, msg.id, publish_event))
    return msg


@router.websocket("/ws/sessions/{session_id}")
async def ws_session(websocket: WebSocket, session_id: UUID) -> None:
    """WebSocket endpoint for receiving real-time chat updates.

    Clients connect to receive message events, tool calls, and AI responses.
    """
    channel = await hub.get(_get_channel_key(session_id))
    await channel.connect(websocket)

    try:
        # Keep connection alive and handle client-initiated closure
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as e:
        logger.error("WebSocket error for session %s: %s", session_id, e)
    finally:
        await channel.disconnect(websocket)
