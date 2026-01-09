from __future__ import annotations

import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "trading-research-api"
    environment: str = os.getenv("ENV", "local")
    db_url: str = os.getenv("DB_URL", "sqlite:///./registry.sqlite")
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")
    cors_allow_origins: list[str] = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")


settings = Settings()
