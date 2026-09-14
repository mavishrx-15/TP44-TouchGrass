"""Database connection. One engine for the whole process, one session per request."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url or "sqlite:///./touchgrass.db")
SessionLocal = sessionmaker(bind=engine)


def get_session():
    """FastAPI dependency. Opens a session for one request and closes it after."""
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
