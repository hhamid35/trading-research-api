from __future__ import annotations

import os
from ..settings import settings
from ..services import storage


def get_checkpointer():
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except Exception:
        return None
    storage.ensure_dirs()
    path = os.path.join(settings.storage_dir, "checkpoints.sqlite")
    return SqliteSaver(path)
