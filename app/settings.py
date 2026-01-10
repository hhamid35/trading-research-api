from __future__ import annotations

import os
from pydantic import BaseModel, SecretStr


class Settings(BaseModel):
    app_name: str = "trading-research-api"
    environment: str = os.getenv("ENV", "local")
    db_url: str = os.getenv("DB_URL", "sqlite:///./registry.sqlite")
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")
    cors_allow_origins: list[str] = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5176").split(",")
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_openai_model: str = os.getenv("LLM_OPENAI_MODEL", "gpt-4o-mini")
    vector_db_provider: str = os.getenv("VECTOR_DB_PROVIDER", "qdrant")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "rag_chunks")
    search_provider: str = os.getenv("SEARCH_PROVIDER", "searxng")
    searxng_url: str = os.getenv("SEARXNG_URL", "http://localhost:8080")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    openai_api_key: SecretStr = SecretStr(os.getenv("OPENAI_API_KEY", ""))
    sentence_transformers_model: str = os.getenv("SENTENCE_TRANSFORMERS_MODEL", "all-MiniLM-L6-v2")


settings = Settings()
