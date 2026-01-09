from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine
from .config import settings

engine = create_engine(settings.db_url, echo=False)


def init_db() -> None:
    # Import models to register tables
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
