from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import dataclass
from typing import Any, Callable, List, Optional
from uuid import UUID

from langchain_core.tools import tool
from sqlmodel import Session

from ..db import engine
from ..indexing.retrieval import retrieve as retrieve_chunks
from ..models import IngestionJob, Source
from ..services import storage
from ..web.fetcher import fetch_url as fetcher_fetch_url
from ..web.search_provider import get_search_provider
from ..workflows.ingestion_graph import run_ingestion_job


@dataclass
class ToolContext:
    session_id: UUID


def _write_source_text(title: str, text: str) -> Source:
    storage.ensure_dirs()
    dest_dir = storage.sources_dir()
    filename = f"{title.replace(' ', '_')}.txt" or "note.txt"
    path = os.path.join(dest_dir, filename)
    i = 1
    base, ext = os.path.splitext(path)
    while os.path.exists(path):
        path = f"{base}_{i}{ext}"
        i += 1

    data = text.encode("utf-8")
    checksum = hashlib.sha256(data).hexdigest()
    with open(path, "wb") as f:
        f.write(data)

    src = Source(
        kind="TEXT",
        title=title,
        filename=os.path.basename(path),
        uri="",
        content_type="text/plain",
        checksum_sha256=checksum,
        bytes=len(data),
        storage_path=path,
        notes=None,
        tags=[],
        metadata_={},
    )
    with Session(engine) as session:
        session.add(src)
        session.commit()
        session.refresh(src)
    return src


def build_tools(context: ToolContext):
    @tool
    def web_search(
        query: str,
        recency_days: Optional[int] = None,
        domain_allowlist: Optional[list[str]] = None,
        limit: int = 10,
    ) -> List[dict]:
        """Search the web for relevant documents."""
        provider = get_search_provider()
        results = provider.search(
            query,
            limit=limit,
            recency_days=recency_days,
            domain_allowlist=domain_allowlist,
        )
        return [r.__dict__ for r in results]

    @tool
    def fetch_url(url: str) -> dict:
        """Fetch a URL, extract text, and store as Source."""
        fetched = fetcher_fetch_url(url)
        src = _write_source_text(fetched.title or "Fetched URL", fetched.text)
        src.kind = "URL"
        src.uri = url
        with Session(engine) as session:
            session.add(src)
            session.commit()
            session.refresh(src)
        return {"source_id": str(src.id), "title": src.title, "uri": src.uri}

    @tool
    def create_note(title: str, text: str) -> dict:
        """Create a note Source from raw text."""
        src = _write_source_text(title, text)
        src.kind = "NOTE"
        with Session(engine) as session:
            session.add(src)
            session.commit()
            session.refresh(src)
        return {"source_id": str(src.id), "title": src.title}

    @tool
    def upload_source(filename: str, content: str) -> dict:
        """Upload a raw file payload into Sources."""
        src = _write_source_text(filename or "upload", content)
        src.kind = "UPLOAD"
        with Session(engine) as session:
            session.add(src)
            session.commit()
            session.refresh(src)
        return {"source_id": str(src.id), "title": src.title}

    @tool
    def index_source(source_id: str, config: Optional[dict] = None) -> dict:
        """Create an ingestion job and index the source."""
        with Session(engine) as session:
            job = IngestionJob(
                source_id=UUID(source_id),
                status="QUEUED",
                attempts=0,
                last_error=None,
                thread_id=f"ingest:{source_id}",
                config_json=config or {},
                stats_json={},
            )
            session.add(job)
            session.commit()
            session.refresh(job)
        asyncio.create_task(run_ingestion_job(job.id))
        return {"job_id": str(job.id), "status": job.status}

    @tool
    def retrieve(query: str, source_id: Optional[str] = None, k: int = 8) -> List[dict]:
        """Retrieve chunks from the vector store."""
        with Session(engine) as session:
            hits = retrieve_chunks(
                session,
                query=query,
                k=k,
                source_id=UUID(source_id) if source_id else None,
            )
        return hits

    return [web_search, fetch_url, create_note, upload_source, index_source, retrieve]
