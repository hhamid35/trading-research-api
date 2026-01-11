from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from qdrant_client.http import models as rest
from sqlmodel import Session, select

from ..models import DocumentChunk
from .embeddings import get_embedding_provider
from .vectorstore import search_vectors


def _build_filter(source_id: Optional[UUID]) -> Optional[rest.Filter]:
    if not source_id:
        return None
    return rest.Filter(
        must=[
            rest.FieldCondition(
                key="source_id", match=rest.MatchValue(value=str(source_id))
            )
        ]
    )


def retrieve(
    session: Session, query: str, k: int = 8, source_id: Optional[UUID] = None
) -> List[dict]:
    provider = get_embedding_provider()
    query_vec = provider.embed_texts([query])[0]
    hits = search_vectors(query_vec, limit=k, filters=_build_filter(source_id))

    chunk_ids = [UUID(str(hit.payload.get("chunk_id"))) for hit in hits if hit.payload]
    chunks = (
        session.exec(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))).all()
        if chunk_ids
        else []
    )
    chunks_by_id = {c.id: c for c in chunks}

    results = []
    for hit in hits:
        payload = hit.payload or {}
        chunk_id = payload.get("chunk_id")
        if not chunk_id:
            continue
        chunk = chunks_by_id.get(UUID(str(chunk_id)))
        if not chunk:
            continue
        results.append(
            {
                "score": hit.score,
                "chunk_id": str(chunk.id),
                "source_id": str(chunk.source_id),
                "document_id": str(chunk.document_id),
                "text": chunk.text,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
            }
        )
    return results
