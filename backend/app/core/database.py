"""
Database engine and session factory.

We use SQLAlchemy 2.x with the new-style Session context manager.
The `get_db` dependency yields a session per request and always closes it.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

# `pool_pre_ping=True` avoids stale-connection errors after long idle periods
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)

# `autocommit=False` so we explicitly commit; `autoflush=False` for control
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """
    FastAPI dependency that provides a database session.
    Guarantees the session is closed even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()