from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Create the SQLAlchemy engine connected to PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# Factory for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and guarantees it is closed when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
