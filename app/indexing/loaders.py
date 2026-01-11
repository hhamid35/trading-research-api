from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List

from bs4 import BeautifulSoup
from readability import Document as ReadabilityDocument


@dataclass
class LoadedDocument:
    kind: str
    title: str
    uri: str
    text: str
    metadata: dict


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\t", " ").split())


def load_text_blob(text: str, title: str = "", uri: str = "") -> List[LoadedDocument]:
    normalized = _normalize_text(text)
    return [
        LoadedDocument(kind="text", title=title, uri=uri, text=normalized, metadata={})
    ]


def load_html(html: str, uri: str = "") -> List[LoadedDocument]:
    doc = ReadabilityDocument(html)
    summary = doc.summary(html_partial=True)
    soup = BeautifulSoup(summary, "html.parser")
    text = soup.get_text("\n", strip=True)
    title = doc.short_title() or "Untitled"
    return [
        LoadedDocument(
            kind="html",
            title=title,
            uri=uri,
            text=_normalize_text(text),
            metadata={"title": title},
        )
    ]


def load_file(path: str, uri: str = "") -> Iterable[LoadedDocument]:
    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return []

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")

    if ext in {".html", ".htm"}:
        return load_html(text, uri=uri)
    if ext in {".md", ".markdown"}:
        return load_text_blob(text, title=os.path.basename(path), uri=uri)
    if ext in {".txt", ".log"}:
        return load_text_blob(text, title=os.path.basename(path), uri=uri)

    return load_text_blob(text, title=os.path.basename(path), uri=uri)
