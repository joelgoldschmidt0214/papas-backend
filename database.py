"""
Database configuration and connection management for TOMOSU Backend API.

Provides production-ready database connection with optimized pooling,
health checks, and proper error handling.
"""

import logging
import time
from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError

from config import Settings
from logging_config import get_logger, log_database_operation, log_error

logger = get_logger(__name__)


class DatabaseManager:
    """
    Database connection manager with optimized pooling and health monitoring.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._is_initialized = False
        self._connection_test_query = text("SELECT 1")

    def initialize(self) -> bool:
        """
        Initialize database engine and session factory.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing database connection...")

            # Create database engine with optimized settings
            self.engine = self._create_engine()

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            # Test connection
            if not self._test_connection():
                logger.error("Database connection test failed")
                return False

            self._is_initialized = True
            logger.info(
                f"Database initialized successfully - "
                f"Pool size: {self.settings.db_pool_size}, "
                f"Max overflow: {self.settings.db_max_overflow}"
            )
            return True

        except Exception as e:
            log_error(logger, e, {"operation": "database_initialization"})
            return False

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with optimized settings"""

        # Connection arguments
        connect_args = self.settings.get_database_connect_args()

        # Add connection timeout
        connect_args.update(
            {
                "connect_timeout": self.settings.db_pool_timeout,
                "read_timeout": self.settings.db_pool_timeout,
                "write_timeout": self.settings.db_pool_timeout,
            }
        )

        # Create engine with connection pooling
        engine = create_engine(
            self.settings.database_url,
            # Connection Pool Configuration
            poolclass=QueuePool,
            pool_size=self.settings.db_pool_size,
            max_overflow=self.settings.db_max_overflow,
            pool_timeout=self.settings.db_pool_timeout,
            pool_recycle=self.settings.db_pool_recycle,
            pool_pre_ping=self.settings.db_pool_pre_ping,
            # Connection Arguments
            connect_args=connect_args,
            # Logging
            echo=self.settings.db_echo,
            echo_pool=self.settings.is_development,
            # Performance Settings
            isolation_level="READ_COMMITTED",
            # Error Handling
            pool_reset_on_return="commit",
        )

        # Add event listeners for monitoring
        self._add_event_listeners(engine)

        return engine

    def _add_event_listeners(self, engine: Engine) -> None:
        """Add event listeners for database monitoring"""

        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Handle new database connections"""
            logger.debug("New database connection established")

            # Set connection-specific settings for MySQL
            with dbapi_connection.cursor() as cursor:
                # Set session timeout
                cursor.execute(
                    "SET SESSION wait_timeout = %s", (self.settings.db_pool_recycle,)
                )
                cursor.execute(
                    "SET SESSION interactive_timeout = %s",
                    (self.settings.db_pool_recycle,),
                )

                # Set charset and collation
                cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")

                # Set SQL mode for strict data handling
                cursor.execute(
                    "SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'"
                )

        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            logger.debug("Database connection checked out from pool")

        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Handle connection checkin to pool"""
            logger.debug("Database connection checked in to pool")

        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation"""
            logger.warning(f"Database connection invalidated: {exception}")

        if self.settings.is_development:

            @event.listens_for(engine, "before_cursor_execute")
            def before_cursor_execute(
                conn, cursor, statement, parameters, context, executemany
            ):
                """Log SQL queries in development"""
                context._query_start_time = time.time()

            @event.listens_for(engine, "after_cursor_execute")
            def after_cursor_execute(
                conn, cursor, statement, parameters, context, executemany
            ):
                """Log SQL query completion in development"""
                total = time.time() - context._query_start_time
                log_database_operation(
                    logger,
                    "EXECUTE",
                    statement.split()[0] if statement else "UNKNOWN",
                    total,
                    cursor.rowcount if hasattr(cursor, "rowcount") else None,
                )

    def _test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(self._connection_test_query)
                result.fetchone()
                logger.debug("Database connection test successful")
                return True
        except Exception as e:
            log_error(logger, e, {"operation": "connection_test"})
            return False

    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session with proper cleanup.

        Yields:
            Session: SQLAlchemy session
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")

        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            log_error(logger, e, {"operation": "session_error"})
            raise
        finally:
            session.close()

    @contextmanager
    def get_session_context(self):
        """
        Context manager for database sessions.

        Usage:
            with db_manager.get_session_context() as session:
                # Use session here
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            log_error(logger, e, {"operation": "session_context_error"})
            raise
        finally:
            session.close()

    def health_check(self) -> dict:
        """
        Perform database health check.

        Returns:
            dict: Health check results
        """
        if not self._is_initialized:
            return {
                "status": "unhealthy",
                "error": "Database not initialized",
                "details": {},
            }

        try:
            start_time = time.time()

            # Test basic connectivity
            with self.engine.connect() as connection:
                connection.execute(self._connection_test_query)

            response_time = time.time() - start_time

            # Get pool status
            pool = self.engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                # pool.invalid() を pool.status() に変更
                "pool_status_summary": pool.status(),
            }

            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "pool_status": pool_status,
                "details": {
                    "pool_size": self.settings.db_pool_size,
                    "max_overflow": self.settings.db_max_overflow,
                    "pool_timeout": self.settings.db_pool_timeout,
                    "pool_recycle": self.settings.db_pool_recycle,
                },
            }

        except Exception as e:
            log_error(logger, e, {"operation": "health_check"})
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"error_type": type(e).__name__},
            }

    def get_pool_stats(self) -> dict:
        """
        Get detailed connection pool statistics.

        Returns:
            dict: Pool statistics
        """
        if not self._is_initialized or not self.engine:
            return {"error": "Database not initialized"}

        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in_connections": pool.checkedin(),
            "checked_out_connections": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            # pool.invalid() は廃止されたため削除
            # "invalid_connections": pool.invalid(),
            "total_connections": pool.size() + pool.overflow(),
            "available_connections": pool.checkedin(),
            "utilization_percentage": round(
                (pool.checkedout() / (pool.size() + pool.overflow())) * 100, 2
            )
            if (pool.size() + pool.overflow()) > 0
            else 0,
            "configuration": {
                "max_pool_size": self.settings.db_pool_size,
                "max_overflow": self.settings.db_max_overflow,
                "pool_timeout": self.settings.db_pool_timeout,
                "pool_recycle_seconds": self.settings.db_pool_recycle,
            },
        }

    def close(self) -> None:
        """Close database connections and cleanup"""
        if self.engine:
            logger.info("Closing database connections...")
            self.engine.dispose()
            self._is_initialized = False
            logger.info("Database connections closed")

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._is_initialized


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def initialize_database(settings: Settings) -> bool:
    """
    Initialize global database manager.

    Args:
        settings: Application settings

    Returns:
        bool: True if initialization successful
    """
    global db_manager

    db_manager = DatabaseManager(settings)
    return db_manager.initialize()


def get_database_manager() -> DatabaseManager:
    """
    Get global database manager instance.

    Returns:
        DatabaseManager: Database manager instance

    Raises:
        RuntimeError: If database not initialized
    """
    if db_manager is None:
        raise RuntimeError(
            "Database not initialized. Call initialize_database() first."
        )
    return db_manager


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        Session: SQLAlchemy session
    """
    manager = get_database_manager()
    yield from manager.get_session()


def get_db_health() -> dict:
    """
    Get database health status.

    Returns:
        dict: Health status
    """
    try:
        manager = get_database_manager()
        return manager.health_check()
    except RuntimeError:
        return {
            "status": "unhealthy",
            "error": "Database not initialized",
            "details": {},
        }


def get_db_stats() -> dict:
    """
    Get database connection pool statistics.

    Returns:
        dict: Pool statistics
    """
    try:
        manager = get_database_manager()
        return manager.get_pool_stats()
    except RuntimeError:
        return {"error": "Database not initialized"}
