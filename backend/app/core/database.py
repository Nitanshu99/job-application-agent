"""
Database connection and session management for the Job Automation System.

This module handles database connectivity, session management, and provides
utilities for database operations using SQLAlchemy with async support.

Features:
- Async SQLAlchemy engine and session management
- Connection pooling and health checking
- Database initialization and migration support
- Transaction management utilities
- Database health monitoring
"""

import logging
import asyncio
from typing import AsyncGenerator, Optional, Any, Dict
from contextlib import asynccontextmanager

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy import event, text

from app.core.config import get_settings

# Get settings
settings = get_settings()

# Setup logging
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker] = None
        self._initialized = False
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine
    
    @property
    def sessionmaker(self) -> async_sessionmaker:
        """Get the session maker."""
        if self._sessionmaker is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._sessionmaker
    
    async def initialize(self) -> None:
        """Initialize database connection and session factory."""
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            # Create async engine
            self._engine = create_async_engine(
                self._get_database_url(),
                **self._get_engine_config()
            )
            
            # Create async session factory
            self._sessionmaker = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Set up event listeners
            self._setup_event_listeners()
            
            # Test connection
            await self._test_connection()
            
            self._initialized = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            self._initialized = False
            logger.info("Database connections closed")
    
    def _get_database_url(self) -> str:
        """Get the database URL for async operations."""
        db_url = str(settings.database_url)
        
        # Convert to async URL if needed
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("sqlite:"):
            db_url = db_url.replace("sqlite:", "sqlite+aiosqlite:", 1)
        
        return db_url
    
    def _get_engine_config(self) -> Dict[str, Any]:
        """Get engine configuration."""
        config = {
            "echo": settings.database_echo,
            "pool_pre_ping": True,
            "pool_recycle": settings.database_pool_recycle,
        }
        
        # Configure pooling based on database type
        if "sqlite" in str(settings.database_url):
            # SQLite doesn't support connection pooling
            config.update({
                "poolclass": NullPool,
                "connect_args": {"check_same_thread": False}
            })
        else:
            # PostgreSQL with connection pooling
            config.update({
                "poolclass": QueuePool,
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_timeout": settings.database_pool_timeout,
            })
        
        return config
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners."""
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and integrity."""
            if "sqlite" in str(settings.database_url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA temp_store=memory")
                cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
                cursor.close()
        
        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout (debug mode only)."""
            if settings.debug:
                logger.debug("Connection checked out from pool")
        
        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin (debug mode only)."""
            if settings.debug:
                logger.debug("Connection checked in to pool")
    
    async def _test_connection(self) -> None:
        """Test database connection."""
        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchall()
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    async def create_all_tables(self) -> None:
        """Create all database tables."""
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("All database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def drop_all_tables(self) -> None:
        """Drop all database tables (use with caution!)."""
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics."""
        try:
            async with self.sessionmaker() as session:
                if "postgresql" in str(settings.database_url):
                    # PostgreSQL specific queries
                    result = await session.execute(text("""
                        SELECT 
                            version() as version,
                            current_database() as database_name,
                            pg_database_size(current_database()) as database_size,
                            (SELECT count(*) FROM information_schema.tables 
                             WHERE table_schema = 'public') as table_count
                    """))
                    row = result.fetchone()
                    
                    return {
                        "database_type": "PostgreSQL",
                        "version": row.version if row else "Unknown",
                        "database_name": row.database_name if row else "Unknown",
                        "database_size": row.database_size if row else 0,
                        "table_count": row.table_count if row else 0,
                    }
                    
                elif "sqlite" in str(settings.database_url):
                    # SQLite specific queries
                    result = await session.execute(text("SELECT sqlite_version()"))
                    version = result.scalar()
                    
                    result = await session.execute(text("""
                        SELECT count(*) FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """))
                    table_count = result.scalar()
                    
                    return {
                        "database_type": "SQLite",
                        "version": version or "Unknown",
                        "database_name": "main",
                        "table_count": table_count or 0,
                    }
                
                else:
                    return {"database_type": "Unknown"}
                    
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}
    
    async def check_health(self) -> Dict[str, Any]:
        """Check database health."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.sessionmaker() as session:
                await session.execute(text("SELECT 1"))
                
            response_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "pool_size": self._engine.pool.size() if hasattr(self._engine.pool, 'size') else None,
                "checked_out": self._engine.pool.checkedout() if hasattr(self._engine.pool, 'checkedout') else None,
            }
            
        except Exception as e:
            response_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": response_time,
            }


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with db_manager.sessionmaker() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with db_manager.sessionmaker() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database transactions.
    
    Automatically commits on success or rolls back on error.
    
    Yields:
        AsyncSession: Database session within a transaction
    """
    async with db_manager.sessionmaker() as session:
        try:
            await session.begin()
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and create tables."""
    await db_manager.initialize()
    await db_manager.create_all_tables()


async def close_db() -> None:
    """Close database connections."""
    await db_manager.close()


async def reset_db() -> None:
    """Reset database by dropping and recreating all tables."""
    logger.warning("Resetting database - all data will be lost!")
    await db_manager.drop_all_tables()
    await db_manager.create_all_tables()


async def check_db_health() -> Dict[str, Any]:
    """Check database health and return status."""
    return await db_manager.check_health()


async def get_db_info() -> Dict[str, Any]:
    """Get database information and statistics."""
    return await db_manager.get_database_info()


class DatabaseService:
    """Service class for common database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query result
        """
        try:
            result = await self.session.execute(text(query), params or {})
            return result
        except SQLAlchemyError as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    async def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Fetch one row from query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Single row or None
        """
        result = await self.execute_query(query, params)
        return result.fetchone()
    
    async def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> list:
        """
        Fetch all rows from query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of rows
        """
        result = await self.execute_query(query, params)
        return result.fetchall()
    
    async def execute_script(self, script: str) -> None:
        """
        Execute SQL script with multiple statements.
        
        Args:
            script: SQL script string
        """
        try:
            statements = [stmt.strip() for stmt in script.split(';') if stmt.strip()]
            for statement in statements:
                await self.session.execute(text(statement))
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Script execution error: {e}")
            raise


# Utility functions for pagination
def paginate_query(query, page: int = 1, page_size: int = 20):
    """
    Add pagination to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Paginated query
    """
    offset = (page - 1) * page_size
    return query.offset(offset).limit(page_size)


async def count_query_results(session: AsyncSession, query) -> int:
    """
    Count total results for a query.
    
    Args:
        session: Database session
        query: SQLAlchemy query object
        
    Returns:
        Total count of results
    """
    count_query = query.statement.with_only_columns(sa.func.count()).order_by(None)
    result = await session.execute(count_query)
    return result.scalar()


# Database event handlers
async def on_startup():
    """Database startup event handler."""
    logger.info("Initializing database connection...")
    await init_db()


async def on_shutdown():
    """Database shutdown event handler."""
    logger.info("Closing database connection...")
    await close_db()