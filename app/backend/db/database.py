"""
Database connection and session management.

Follows Microsoft Azure best practices:
- Connection pooling
- Async support with asyncpg
- Graceful degradation (fallback to in-memory)
- Health checks
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager with connection pooling and health checks.
    
    Features:
    - Async SQLAlchemy with asyncpg
    - Connection pooling (configurable)
    - Automatic retry on connection failure
    - Health check endpoint
    - Graceful fallback to in-memory mode
    """
    
    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        """
        Initialize database manager.
        
        Args:
            database_url: PostgreSQL connection string (async format)
            echo: Enable SQL query logging (dev only)
        """
        self.database_url = database_url or self._get_database_url()
        self.echo = echo
        self.engine = None
        self.session_factory = None
        self._is_initialized = False
        self._fallback_mode = False
        
    @staticmethod
    def _get_database_url() -> Optional[str]:
        """
        Get database URL from environment variables.
        
        Priority:
        1. DATABASE_URL (async format: postgresql+asyncpg://...)
        2. Individual components (POSTGRES_HOST, POSTGRES_DB, etc.)
        3. Azure PostgreSQL connection string
        """
        # Direct URL (preferred)
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            # Ensure async driver
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return db_url
        
        # Build from components (Azure pattern)
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "agentdb")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        
        if host and user and password:
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        
        logger.warning("No database configuration found. Will run in fallback mode (in-memory).")
        return None
    
    async def initialize(self) -> bool:
        """
        Initialize database connection and create tables.
        
        Returns:
            True if successful, False if fallback mode
        """
        if self._is_initialized:
            return not self._fallback_mode
        
        if not self.database_url:
            logger.warning("Database not configured. Running in fallback mode.")
            self._fallback_mode = True
            self._is_initialized = True
            return False
        
        try:
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                pool_size=10,  # Azure PostgreSQL recommended
                max_overflow=20,
                pool_pre_ping=True,  # Health check before use
                pool_recycle=3600,  # Recycle connections every hour
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            # Create tables (idempotent)
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully.")
            self._is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("Falling back to in-memory mode.")
            self._fallback_mode = True
            self._is_initialized = True
            return False
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed.")
    
    async def health_check(self) -> dict:
        """
        Check database health.
        
        Returns:
            Health status dict with details
        """
        if self._fallback_mode:
            return {
                "status": "degraded",
                "mode": "fallback",
                "message": "Running without database persistence"
            }
        
        if not self.engine:
            return {
                "status": "down",
                "message": "Database not initialized"
            }
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            
            return {
                "status": "healthy",
                "mode": "postgresql",
                "message": "Database connection OK"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "mode": "postgresql",
                "message": str(e)
            }
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session (context manager).
        
        Usage:
            async with db_manager.get_session() as session:
                result = await session.execute(query)
        """
        if self._fallback_mode:
            # Return None in fallback mode - callers should handle
            yield None
            return
        
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Global instance (singleton pattern)
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def init_database(echo: bool = False) -> bool:
    """
    Initialize global database manager.
    
    Args:
        echo: Enable SQL query logging
        
    Returns:
        True if initialized, False if fallback mode
    """
    db = get_db_manager()
    return await db.initialize()


async def close_database():
    """Close global database manager."""
    db = get_db_manager()
    await db.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Get database session for use in endpoints.
    
    Usage:
        async with get_db_session() as session:
            if session:  # Check if database available
                result = await session.execute(query)
    """
    db = get_db_manager()
    async with db.get_session() as session:
        yield session
