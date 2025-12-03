"""Database connection and initialization.

Supports both SQLite (local development) and PostgreSQL (production/Supabase).

Environment variables:
- SANDBOXY_DATABASE_URL: Full database URL (e.g., postgresql+asyncpg://...)
- SANDBOXY_DB_PATH: Path to SQLite file (default: ~/.sandboxy/sandboxy.db)
- SANDBOXY_DB_ECHO: Set to "true" to log SQL queries

Examples:
- Local SQLite: (default, no env vars needed)
- PostgreSQL: SANDBOXY_DATABASE_URL=postgresql+asyncpg://user:pass@host/db
- Supabase: SANDBOXY_DATABASE_URL=postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from sandboxy.db.models import Base

# Default database path for SQLite
DEFAULT_DB_PATH = Path.home() / ".sandboxy" / "sandboxy.db"


def get_database_url() -> str:
    """Get the database URL from environment or use default SQLite.

    Returns:
        Database URL string for SQLAlchemy async engine.
    """
    db_url = os.environ.get("SANDBOXY_DATABASE_URL")
    if db_url:
        # Convert standard postgres:// to postgresql+asyncpg://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return db_url

    # Default to SQLite in user's home directory
    db_path = os.environ.get("SANDBOXY_DB_PATH", str(DEFAULT_DB_PATH))
    return f"sqlite+aiosqlite:///{db_path}"


def _create_engine():
    """Create the async engine with appropriate settings."""
    db_url = get_database_url()
    is_sqlite = db_url.startswith("sqlite")

    # Use NullPool for PostgreSQL to work better with serverless/Supabase
    pool_class = None if is_sqlite else NullPool

    return create_async_engine(
        db_url,
        echo=os.environ.get("SANDBOXY_DB_ECHO", "").lower() == "true",
        poolclass=pool_class,
    )


# Create async engine
engine = _create_engine()

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize the database, creating tables if needed.

    For SQLite: Creates the directory and database file.
    For PostgreSQL: Creates tables (assumes database already exists).

    Note: For production PostgreSQL/Supabase, consider using Alembic migrations
    instead of create_all() for better schema management.
    """
    db_url = get_database_url()

    # Ensure directory exists for SQLite
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for dependency injection.

    Usage with FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
