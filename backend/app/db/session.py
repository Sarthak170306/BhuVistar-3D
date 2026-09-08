from collections.abc import Generator
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

# Create SQLAlchemy 2.x Engine with psycopg3 and local development pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
)

# Session factory for generating transactional database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields an independent database session per request
    and guarantees proper closing upon completion or exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict[str, Any]:
    """
    Performs a database connectivity test:
    1. Opens a SQLAlchemy connection using DATABASE_URL.
    2. Executes SELECT 1;
    3. Executes SELECT version();
    4. Executes SELECT PostGIS_Version();
    5. Returns a clear success response without leaking credentials.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            pg_version = conn.execute(text("SELECT version();")).scalar()
            postgis_version = conn.execute(text("SELECT PostGIS_Version();")).scalar()

            return {
                "database": "connected",
                "postgresql": str(pg_version),
                "postgis": str(postgis_version),
            }
    except Exception:
        return {
            "database": "disconnected",
            "error": "Database connection failed",
        }

