from __future__ import annotations

from typing import Iterable, List

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from ..settings import settings


def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(dim: int) -> None:
    client = get_client()
    collections = client.get_collections().collections
    if any(c.name == settings.qdrant_collection for c in collections):
        return
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=rest.VectorParams(size=dim, distance=rest.Distance.COSINE),
    )


def upsert_vectors(items: Iterable[rest.PointStruct]) -> None:
    client = get_client()
    client.upsert(collection_name=settings.qdrant_collection, points=list(items))


def search_vectors(query: List[float], limit: int = 8, filters: rest.Filter | None = None) -> List[rest.ScoredPoint]:
    client = get_client()
    return client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query,
        limit=limit,
        query_filter=filters,
    )
