from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import engine
from ..models import ResearchChatMessage, HypothesisDraft, HypothesisCard
from ..indexing.retrieval import retrieve
from ..settings import settings
from .state import HypothesisState


class HypothesisPayload(BaseModel):
    name: str
    mechanism: str
    falsifiable_prediction: str
    null_hypothesis: str = "No conditional edge after costs."
    decision_timing: str = "on_trade_event"
    horizons_ms: List[int] = Field(default_factory=list)
    primary_metrics: List[str] = Field(default_factory=list)
    acceptance_criteria: List[dict] = Field(default_factory=list)
    failure_modes: List[str] = Field(default_factory=list)
    tradability_constraints: str = ""


def _chat_context(session_id: UUID, limit: int = 12) -> str:
    with Session(engine) as session:
        messages = session.exec(
            select(ResearchChatMessage)
            .where(ResearchChatMessage.session_id == session_id)
            .order_by(ResearchChatMessage.created_at.desc())
            .limit(limit)
        ).all()
    lines = [f"{m.role}: {m.content}" for m in reversed(messages)]
    return "\n".join(lines)


def run_hypothesis_graph(session_id: UUID) -> HypothesisDraft:
    context = _chat_context(session_id)

    with Session(engine) as session:
        hits = retrieve(session, query="draft a falsifiable hypothesis", k=6)

    citations = [
        {
            "chunk_id": hit["chunk_id"],
            "source_id": hit["source_id"],
            "document_id": hit["document_id"],
            "char_start": hit["char_start"],
            "char_end": hit["char_end"],
            "quote": hit["text"][:300],
        }
        for hit in hits
    ]

    model = ChatOpenAI(model=settings.llm_openai_model, api_key=settings.openai_api_key)
    structured = model.with_structured_output(HypothesisPayload)

    prompt = (
        "Draft a non-generic, falsifiable trading hypothesis. "
        "Use the context and citations."
    )
    output = structured.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=context),
        HumanMessage(content=f"Citations: {citations}"),
    ])

    payload = output.model_dump()
    draft = HypothesisDraft(
        session_id=session_id,
        status="PROPOSED",
        payload_json=payload,
        citations_json=citations,
        rationale_json={"summary": "Drafted from chat context"},
        thread_id=f"hypothesis:{session_id}",
        created_by="local-user",
        created_at=datetime.utcnow(),
    )
    with Session(engine) as session:
        session.add(draft)
        session.commit()
        session.refresh(draft)
    return draft


def approve_hypothesis(draft_id: UUID, approved_by: str = "local-user") -> HypothesisCard:
    with Session(engine) as session:
        draft = session.get(HypothesisDraft, draft_id)
        if not draft:
            raise RuntimeError("Draft not found")
        payload = draft.payload_json
        card = HypothesisCard(**payload)
        card.status = "APPROVED"
        card.approved_at = datetime.utcnow()
        card.approved_by = approved_by
        session.add(card)
        draft.status = "APPROVED"
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
        session.refresh(card)
        return card
