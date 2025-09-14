"""
SQLAlchemy Base Configuration

Sets up the declarative base and database configuration for all models.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path

# Database configuration
DATABASE_PATH = Path(__file__).parent.parent.parent / "data" / "dev.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models"""
    pass

# Async engine for all database operations
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False  # Set to True for SQL debugging
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# FastAPI dependency for database sessions
async def get_async_session():
    """Dependency that provides async database sessions to FastAPI routes"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()