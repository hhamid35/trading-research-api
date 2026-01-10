from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ..db import get_session
from ..indexing.retrieval import retrieve
from ..schemas.research import RetrievalHitOut

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[RetrievalHitOut])
def search(query: str = Query(..., alias="q"), k: int = 8, source_id: Optional[UUID] = None, session: Session = Depends(get_session)):
    return retrieve(session, query=query, k=k, source_id=source_id)
