from __future__ import annotations

import os
from psycopg import Connection

from langgraph.checkpoint.postgres import PostgresSaver

from ..config import get_settings
from ..services import storage


def get_checkpointer() -> PostgresSaver:
    storage.ensure_dirs()
    settings = get_settings()
    conn = Connection.connect(settings.db_url, autocommit=True)
    return PostgresSaver(conn)