from __future__ import annotations

from sqlmodel import SQLModel, create_engine, Session
from .settings import settings

engine = create_engine(settings.db_url, echo=False)


def create_db_and_tables() -> None:
    # Import models so they are registered with SQLModel metadata
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
