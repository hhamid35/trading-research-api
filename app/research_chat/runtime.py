from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable, Dict, List
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from sqlmodel import Session, select

from ..config import get_settings
from ..db import engine
from ..models import ResearchChatMessage, ResearchChatSession

settings = get_settings()
from .prompts import SYSTEM_PROMPT
from .tools import ToolContext, build_tools

Publisher = Callable[[dict], None]


def _load_history(session_id: UUID) -> List[ResearchChatMessage]:
    with Session(engine) as session:
        return session.exec(
            select(ResearchChatMessage)
            .where(ResearchChatMessage.session_id == session_id)
            .order_by(ResearchChatMessage.created_at.asc())
        ).all()


def _to_lc_messages(history: List[ResearchChatMessage]) -> List:
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        role = msg.role
        if role == "assistant":
            messages.append(AIMessage(content=msg.content))
        elif role == "tool":
            messages.append(
                ToolMessage(content=msg.content, tool_call_id=msg.tool_name or "")
            )
        else:
            messages.append(HumanMessage(content=msg.content))
    return messages


def _save_message(
    session_id: UUID,
    role: str,
    content: str,
    tool_name: str | None = None,
    tool_payload: dict | None = None,
) -> ResearchChatMessage:
    with Session(engine) as session:
        msg = ResearchChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_payload_json=tool_payload,
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
        return msg


async def run_chat_turn(
    session_id: UUID, user_message_id: UUID, publish: Callable[[dict], None]
) -> None:
    history = _load_history(session_id)
    tools = build_tools(ToolContext(session_id=session_id))

    tool_model = ChatOpenAI(
        model=settings.llm_openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    ).bind_tools(tools)

    lc_messages = _to_lc_messages(history)

    max_iters = 3
    for _ in range(max_iters):
        response = await tool_model.ainvoke(lc_messages)
        if not response.tool_calls:
            break
        lc_messages.append(response)
        for call in response.tool_calls:
            publish({"type": "tool_start", "tool": call["name"], "args": call["args"]})
            tool = next((t for t in tools if t.name == call["name"]), None)
            result = tool.invoke(call["args"]) if tool else {"error": "tool not found"}
            tool_msg = _save_message(
                session_id=session_id,
                role="tool",
                content=str(result),
                tool_name=call["name"],
                tool_payload=result if isinstance(result, dict) else {"result": result},
            )
            publish({"type": "tool_end", "tool": call["name"], "result": result})
            lc_messages.append(
                ToolMessage(
                    content=str(result), tool_call_id=call.get("id") or call["name"]
                )
            )
    else:
        publish({"type": "error", "message": "Tool loop exceeded"})
        return

    assistant = _save_message(session_id=session_id, role="assistant", content="")
    publish({"type": "message_created", "message": assistant.model_dump()})

    stream_model = ChatOpenAI(
        model=settings.llm_openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        streaming=True,
    )

    content_parts: List[str] = []
    async for chunk in stream_model.astream(lc_messages):
        delta = chunk.content or ""
        if not delta:
            continue
        content_parts.append(delta)
        publish(
            {"type": "assistant_delta", "message_id": str(assistant.id), "delta": delta}
        )

    final = "".join(content_parts).strip()
    with Session(engine) as session:
        msg = session.get(ResearchChatMessage, assistant.id)
        if msg:
            msg.content = final
            session.add(msg)
            session.commit()
            session.refresh(msg)
            publish({"type": "assistant_done", "message": msg.model_dump()})

    with Session(engine) as session:
        chat = session.get(ResearchChatSession, session_id)
        if chat:
            chat.state_json = {"last_message_at": datetime.utcnow().isoformat()}
            session.add(chat)
            session.commit()
