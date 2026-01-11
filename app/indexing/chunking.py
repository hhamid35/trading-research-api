from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Iterable, List

CHUNK_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


@dataclass
class Chunk:
    id: uuid.UUID
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    token_count: int
    metadata: dict


def _token_count(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text.split()))


def _normalize(text: str) -> str:
    return " ".join(text.replace("\t", " ").split())


def chunk_text(
    text: str, document_id: uuid.UUID, chunk_size: int = 1000, overlap: int = 120
) -> List[Chunk]:
    normalized = _normalize(text)
    chunks: List[Chunk] = []
    start = 0
    index = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        if end < len(normalized):
            end = normalized.rfind(" ", start, end) or end
        chunk_text = normalized[start:end].strip()
        if chunk_text:
            checksum = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            chunk_id = uuid.uuid5(CHUNK_NAMESPACE, f"{document_id}:{index}:{checksum}")
            chunks.append(
                Chunk(
                    id=chunk_id,
                    chunk_index=index,
                    text=chunk_text,
                    char_start=start,
                    char_end=end,
                    token_count=_token_count(chunk_text),
                    metadata={"checksum": checksum},
                )
            )
            index += 1
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def chunk_documents(
    docs: Iterable[tuple[uuid.UUID, str]], chunk_size: int = 1000, overlap: int = 120
) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for document_id, text in docs:
        all_chunks.extend(
            chunk_text(
                text, document_id=document_id, chunk_size=chunk_size, overlap=overlap
            )
        )
    return all_chunks
