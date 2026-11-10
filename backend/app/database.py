"""
VisualGuard AI - Database Configuration and Session Management
=============================================================

This module configures SQLAlchemy connectivity for PostgreSQL, providing:
- Database engine with connection pooling and pre-ping verification.
- SessionLocal factory for scoped database sessions.
- Declarative Base for upcoming Phase 2 models.
- Database session dependency (get_db) for FastAPI endpoints.
- Diagnostic connection checker for health reporting.
"""

from typing import Generator, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Engine configuration for PostgreSQL
# connect_timeout=3 prevents long hangs if the PostgreSQL service is offline
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args={"connect_timeout": 3},
)

# Thread-local database session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative Base for SQLAlchemy models (models will be implemented in Phase 2)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides an isolated SQLAlchemy session per request
    and guarantees it is closed when the request lifecycle ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Tuple[bool, str]:
    """
    Tests live PostgreSQL connectivity by executing 'SELECT 1'.

    Returns:
        Tuple[bool, str]: (is_connected, details_message)
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "PostgreSQL connection successful"
    except Exception as exc:
        return False, f"PostgreSQL connection failed: {str(exc)}"


def ensure_default_user() -> None:
    """
    Ensure at least one default user (user_id=1) exists in the User table
    for linking media uploads prior to user registration/authentication.
    """
    try:
        from app.models.user import User

        with SessionLocal() as db:
            user = db.query(User).filter(User.user_id == 1).first()
            if not user:
                db.add(User(user_id=1))
                db.commit()
    except Exception:
        pass

