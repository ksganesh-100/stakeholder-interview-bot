"""Database engine and session setup.

Uses SQLAlchemy with a SQLite file locally and Postgres in production.
The database is chosen entirely by the DATABASE_URL environment variable:

    - unset            -> sqlite:///./data.db   (local dev)
    - postgres://...   -> normalised to postgresql:// and used as-is (Render)
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data.db")

# Render exposes Postgres URLs as postgres://; SQLAlchemy wants postgresql://.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# check_same_thread is a SQLite-only flag needed for FastAPI's threaded workers.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist. Called once on startup."""
    import models  # noqa: F401  (ensures models are registered on Base)

    Base.metadata.create_all(bind=engine)
