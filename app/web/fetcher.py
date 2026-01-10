from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..indexing.loaders import load_html, load_text_blob


@dataclass
class FetchResult:
    title: str
    text: str
    uri: str
    kind: str


def fetch_url(url: str) -> FetchResult:
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        text = resp.text

    if "text/html" in content_type:
        doc = load_html(text, uri=url)[0]
        return FetchResult(title=doc.title, text=doc.text, uri=url, kind="html")

    doc = load_text_blob(text, title=url, uri=url)[0]
    return FetchResult(title=doc.title, text=doc.text, uri=url, kind="text")
