from __future__ import annotations

from typing import List

from ..config import get_settings

settings = get_settings()


class EmbeddingProvider:
    def model_name(self) -> str:
        raise NotImplementedError

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        from langchain_openai import OpenAIEmbeddings

        self._model = "text-embedding-3-small"
        self._client = OpenAIEmbeddings(
            api_key=settings.openai_api_key, model=self._model
        )

    def model_name(self) -> str:
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self._client.embed_documents(texts)


class SentenceTransformersProvider(EmbeddingProvider):
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model_name = settings.sentence_transformers_model
        self._model = SentenceTransformer(self._model_name)

    def model_name(self) -> str:
        return self._model_name

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(texts, show_progress_bar=False)
        return [v.tolist() for v in vectors]


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider == "sentence_transformers":
        return SentenceTransformersProvider()
    return OpenAIEmbeddingProvider()
