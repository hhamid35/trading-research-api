"""Application configuration with environment variable support."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration with environment variable support."""

    # Application Settings
    app_name: str = Field(
        default="Trading Research API", description="Application name"
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    environment: str = Field(
        default="local", description="Environment name (local, dev, staging, prod)"
    )

    # Database Configuration
    db_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/postgres", description="Database connection string"
    )

    # Storage Configuration
    storage_dir: str = Field(
        default="./storage", description="Directory for file storage"
    )

    # CORS Configuration
    cors_allow_origins: str = Field(
        default="http://localhost:5176",
        description="Comma-separated list of allowed CORS origins",
    )

    # LLM Configuration
    llm_provider: str = Field(
        default="openai", description="LLM provider (openai, anthropic, etc.)"
    )
    llm_openai_model: str = Field(
        default="gpt-4o-mini", description="OpenAI model to use"
    )
    openai_api_key: SecretStr = Field(
        default=SecretStr(""), description="OpenAI API key"
    )

    # Vector Database Configuration
    vector_db_provider: str = Field(
        default="qdrant", description="Vector database provider"
    )
    qdrant_url: str = Field(
        default="http://localhost:6333", description="Qdrant server URL"
    )
    qdrant_collection: str = Field(
        default="rag_chunks", description="Qdrant collection name"
    )

    # Search Configuration
    search_provider: str = Field(default="searxng", description="Web search provider")
    searxng_url: str = Field(
        default="http://localhost:8080", description="SearXNG server URL"
    )

    # Embedding Configuration
    embedding_provider: str = Field(default="openai", description="Embedding provider")
    sentence_transformers_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence transformers model name"
    )

    # Health Check Configuration
    health_check_timeout: float = Field(
        default=5.0, description="Health check timeout in seconds"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow",  # Allow extra fields from environment
    }


def get_settings() -> Settings:
    """
    Get application settings instance.

    This function can be used as a FastAPI dependency.

    Returns:
        Settings instance with configuration from environment
    """
    return Settings()


# Global settings instance for non-dependency usage
settings = get_settings()
