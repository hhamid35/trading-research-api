from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Generator, List
from uuid import UUID

from langgraph.graph import StateGraph
from qdrant_client.http import models as rest
from regex import D
from sqlalchemy import and_, tuple_
from sqlmodel import Session, bindparam, select
from psycopg import Connection
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver

from ..config import get_settings
from ..db import engine
from ..indexing.chunking import chunk_text
from ..indexing.embeddings import get_embedding_provider
from ..indexing.loaders import load_file, load_text_blob
from ..indexing.vectorstore import ensure_collection, upsert_vectors
from ..models import ChunkEmbedding, Document, DocumentChunk, IngestionJob, Source

settings = get_settings()
from ..services import storage
from .checkpoint import get_checkpointer
from .state import IngestionState


def _update_job(job_id: UUID, **updates) -> None:
    with Session(engine) as session:
        job = session.get(IngestionJob, job_id)
        if not job:
            return
        for key, value in updates.items():
            setattr(job, key, value)
        session.add(job)
        session.commit()


def load_source(state: IngestionState) -> IngestionState:
    job_id = UUID(state["job_id"])
    with Session(engine) as session:
        job = session.get(IngestionJob, job_id)
        if not job:
            raise RuntimeError("Ingestion job not found")
        source = session.get(Source, job.source_id)
        if not source:
            raise RuntimeError("Source not found")

        docs = []
        if source.storage_path:
            docs = list(load_file(source.storage_path, uri=source.uri))
        elif source.uri:
            docs = load_text_blob(source.uri, title=source.title, uri=source.uri)
        elif source.notes:
            docs = load_text_blob(source.notes, title=source.title, uri=source.uri)

        document_ids = []
        for doc in docs:
            document = Document(
                source_id=source.id,
                kind=doc.kind,
                title=doc.title,
                uri=doc.uri,
                metadata_json=doc.metadata,
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            document_ids.append(str(document.id))

        return {
            **state,
            "source_id": str(source.id),
            "document_ids": document_ids,
        }


def chunk_documents(state: IngestionState) -> IngestionState:
    document_ids = [UUID(did) for did in state.get("document_ids", [])]
    chunk_ids: List[str] = []
    with Session(engine) as session:
        for doc_id in document_ids:
            doc = session.get(Document, doc_id)
            if not doc:
                continue
            source = session.get(Source, doc.source_id)
            if not source:
                continue
            if source.storage_path:
                loaded_docs = list(load_file(source.storage_path, uri=source.uri))
                text = loaded_docs[0].text if loaded_docs else ""
            else:
                text = source.notes or ""
            chunks = chunk_text(text, document_id=doc.id)
            for chunk in chunks:
                exists = session.get(DocumentChunk, chunk.id)
                if exists:
                    chunk_ids.append(str(exists.id))
                    continue
                row = DocumentChunk(
                    id=chunk.id,
                    document_id=doc.id,
                    source_id=doc.source_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    token_count=chunk.token_count,
                    metadata_json=chunk.metadata,
                )
                session.add(row)
                session.commit()
                chunk_ids.append(str(row.id))
    return {**state, "chunk_ids": chunk_ids}


def embed_chunks(state: IngestionState) -> IngestionState:
    provider = get_embedding_provider()
    model_name = provider.model_name()
    chunk_ids = [UUID(cid) for cid in state.get("chunk_ids", [])]
    if not chunk_ids:
        return {**state, "embedding_model": model_name}

    embeddings = []
    payloads = []
    with Session(engine) as session:
        chunks = session.exec(
            select(DocumentChunk).where(DocumentChunk.id.in_(bindparam("q"))),
            bind_arguments=dict(q=chunk_ids),
        ).all()
        texts = [c.text for c in chunks]
        if not texts:
            return {**state, "embedding_model": model_name}
        vectors = provider.embed_texts(texts)
        ensure_collection(len(vectors[0]))

        for chunk, vector in zip(chunks, vectors):
            source = session.get(Source, chunk.source_id)
            doc = session.get(Document, chunk.document_id)
            checksum = chunk.metadata_json.get("checksum", "") + ":" + model_name
            existing = session.exec(
                select(ChunkEmbedding).where(
                    and_(
                        ChunkEmbedding.chunk_id == chunk.id,
                        ChunkEmbedding.embedding_model == model_name,
                        ChunkEmbedding.checksum == checksum,
                    )
                )
            ).first()
            if existing:
                continue
            embedding = ChunkEmbedding(
                chunk_id=chunk.id,
                embedding_model=model_name,
                vector_id=str(chunk.id),
                dim=len(vector),
                checksum=checksum,
            )
            session.add(embedding)
            session.commit()
            embeddings.append(vector)
            payloads.append(
                {
                    "id": str(chunk.id),
                    "vector": vector,
                    "payload": {
                        "source_id": str(chunk.source_id),
                        "document_id": str(chunk.document_id),
                        "chunk_id": str(chunk.id),
                        "chunk_index": chunk.chunk_index,
                        "title": doc.title if doc else "",
                        "uri": doc.uri if doc else "",
                        "tags": source.tags if source else [],
                        "created_at": chunk.created_at.isoformat(),
                    },
                }
            )

    if payloads:
        points = [
            {
                "id": item["id"],
                "vector": item["vector"],
                "payload": item["payload"],
            }
            for item in payloads
        ]

        upsert_vectors([rest.PointStruct(**p) for p in points])

    return {**state, "embedding_model": model_name}


def mark_complete(state: IngestionState) -> IngestionState:
    job_id = UUID(state["job_id"])
    _update_job(job_id, status="SUCCEEDED", ended_at=datetime.utcnow())
    return state


def _checkpointer() -> PostgresSaver:
    settings = get_settings()
    conn = Connection.connect(
        settings.db_url,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row
    )
    return PostgresSaver(conn)


def build_graph():
    graph = StateGraph(IngestionState)
    graph.add_node("load_source", load_source)
    graph.add_node("chunk_documents", chunk_documents)
    graph.add_node("embed_chunks", embed_chunks)
    graph.add_node("mark_complete", mark_complete)
    graph.set_entry_point("load_source")
    graph.add_edge("load_source", "chunk_documents")
    graph.add_edge("chunk_documents", "embed_chunks")
    graph.add_edge("embed_chunks", "mark_complete")
    return graph.compile(checkpointer=_checkpointer())


async def run_ingestion_job(job_id: UUID, publish=None) -> None:
    _update_job(job_id, status="RUNNING", started_at=datetime.utcnow())
    if publish:
        publish({"type": "status", "status": "RUNNING", "job_id": str(job_id)})
    try:
        graph = build_graph()
        graph.invoke(
            {
                "job_id": str(job_id),
                "source_id": "",
                "document_ids": [],
                "chunk_ids": [],
                "embedding_model": "",
                "stats": {},
                "error": None,
            },
            config={"configurable": {"thread_id": f"ingest:{job_id}"}},
        )
    except Exception as exc:
        _update_job(
            job_id, status="FAILED", last_error=str(exc), ended_at=datetime.utcnow()
        )
        if publish:
            publish(
                {
                    "type": "status",
                    "status": "FAILED",
                    "job_id": str(job_id),
                    "error": str(exc),
                }
            )
        return
    _update_job(job_id, status="SUCCEEDED", ended_at=datetime.utcnow())
    if publish:
        publish({"type": "status", "status": "SUCCEEDED", "job_id": str(job_id)})
