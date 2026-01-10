from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ResearchChatSessionCreate(DTO):
    title: Optional[str] = None


class ResearchChatSessionOut(DTO):
    id: UUID
    title: str
    created_by: str
    created_at: datetime
    state_json: dict = Field(default_factory=dict)


class ResearchChatMessageCreate(DTO):
    content: str


class ResearchChatMessageOut(DTO):
    id: UUID
    session_id: UUID
    role: str
    content: str
    tool_name: Optional[str] = None
    tool_payload_json: Optional[dict] = None
    created_at: datetime


class IngestionJobCreate(DTO):
    source_id: UUID
    config: dict = Field(default_factory=dict)


class IngestionJobOut(DTO):
    id: UUID
    source_id: UUID
    status: str
    attempts: int
    last_error: Optional[str] = None
    thread_id: str
    config_json: dict = Field(default_factory=dict)
    stats_json: dict = Field(default_factory=dict)
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class SearchResultOut(DTO):
    title: str
    url: str
    snippet: str


class RetrievalHitOut(DTO):
    score: float
    chunk_id: str
    source_id: str
    document_id: str
    text: str
    char_start: int
    char_end: int


class HypothesisDraftCreate(DTO):
    session_id: UUID
    constraints: dict = Field(default_factory=dict)


class HypothesisDraftOut(DTO):
    id: UUID
    session_id: UUID
    status: str
    payload_json: dict
    citations_json: list[dict]
    rationale_json: dict
    thread_id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ManifestDraftCreate(DTO):
    hypothesis_id: UUID
    preferences: dict = Field(default_factory=dict)


class ManifestDraftOut(DTO):
    id: UUID
    hypothesis_id: UUID
    status: str
    payload_json: dict
    validation_report_json: dict
    thread_id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
