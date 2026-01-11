from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from ..config import get_settings


def ensure_dirs() -> None:
    settings = get_settings()
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(settings.storage_dir, "sources")).mkdir(
        parents=True, exist_ok=True
    )
    Path(os.path.join(settings.storage_dir, "runs")).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(settings.storage_dir, "patches")).mkdir(
        parents=True, exist_ok=True
    )
    Path(os.path.join(settings.storage_dir, "strategies")).mkdir(
        parents=True, exist_ok=True
    )


def sources_dir() -> str:
    settings = get_settings()
    return os.path.join(settings.storage_dir, "sources")


def runs_dir() -> str:
    settings = get_settings()
    return os.path.join(settings.storage_dir, "runs")


def patches_dir() -> str:
    settings = get_settings()
    return os.path.join(settings.storage_dir, "patches")


def strategies_dir() -> str:
    settings = get_settings()
    return os.path.join(settings.storage_dir, "strategies")


def run_artifacts_dir(run_id: UUID) -> str:
    d = os.path.join(runs_dir(), str(run_id))
    Path(d).mkdir(parents=True, exist_ok=True)
    return d
