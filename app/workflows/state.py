from __future__ import annotations

from typing import List, Optional, TypedDict
from uuid import UUID


class IngestionState(TypedDict):
    job_id: str
    source_id: str
    document_ids: List[str]
    chunk_ids: List[str]
    embedding_model: str
    stats: dict
    error: Optional[str]


class HypothesisState(TypedDict):
    session_id: str
    draft_id: Optional[str]
    citations: List[dict]
    payload: dict
    rationale: dict


class ManifestState(TypedDict):
    hypothesis_id: str
    draft_id: Optional[str]
    payload: dict
    validation: dict
