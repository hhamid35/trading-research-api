from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx

from ..settings import settings


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider:
    def search(self, query: str, limit: int = 10, recency_days: Optional[int] = None, domain_allowlist: Optional[list[str]] = None) -> List[SearchResult]:
        raise NotImplementedError


class SearxngProvider(SearchProvider):
    def __init__(self) -> None:
        self.base_url = settings.searxng_url.rstrip("/")

    def search(self, query: str, limit: int = 10, recency_days: Optional[int] = None, domain_allowlist: Optional[list[str]] = None) -> List[SearchResult]:
        params = {
            "q": query,
            "format": "json",
            "language": "en",
            "safesearch": 0,
        }
        if recency_days:
            params["time_range"] = f"{recency_days}d"
        if domain_allowlist:
            params["q"] += " " + " ".join(f"site:{d}" for d in domain_allowlist)

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", [])[:limit]:
            results.append(
                SearchResult(
                    title=item.get("title") or "Untitled",
                    url=item.get("url") or "",
                    snippet=item.get("content") or "",
                )
            )
        return results


def get_search_provider() -> SearchProvider:
    provider = settings.search_provider.lower()
    if provider == "searxng":
        return SearxngProvider()
    return SearxngProvider()
