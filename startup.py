"""
Production startup script for TOMOSU Backend API.

Handles application initialization, configuration validation,
and graceful startup with proper error handling.
"""

import sys
import os
import asyncio
import signal
import time
from pathlib import Path
from typing import Optional

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings, get_settings
from logging_config import setup_logging, get_logger
from database import initialize_database, get_database_manager
from cache.manager import cache_manager


class ApplicationStartup:
    """Handles application startup and initialization"""

    def __init__(self):
        self.settings: Optional[Settings] = None
        self.logger: Optional = None
        self.startup_time = time.time()
        self.shutdown_requested = False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""

        def signal_handler(signum, frame):
            self.logger.info(
                f"Received signal {signum}, initiating graceful shutdown..."
            )
            self.shutdown_requested = True

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def validate_environment(self) -> bool:
        """Validate environment and configuration"""
        try:
            # Load and validate settings
            self.settings = get_settings()

            # Setup logging first
            setup_logging(self.settings)
            self.logger = get_logger(__name__)

            self.logger.info("=" * 60)
            self.logger.info("TOMOSU Backend API - Starting Up")
            self.logger.info("=" * 60)
            self.logger.info(f"Environment: {self.settings.environment.value}")
            self.logger.info(f"Version: {self.settings.app_version}")
            self.logger.info(f"Debug Mode: {self.settings.debug}")
            self.logger.info(f"Log Level: {self.settings.log_level.value}")

            # Validate critical settings
            if self.settings.is_production:
                if (
                    self.settings.session_secret_key
                    == "dev-secret-key-change-in-production"
                ):
                    self.logger.error(
                        "Production environment requires secure session secret key"
                    )
                    return False

                if self.settings.debug:
                    self.logger.warning(
                        "Debug mode is enabled in production - this is not recommended"
                    )

            # Validate database configuration
            if not all(
                [
                    self.settings.db_user,
                    self.settings.db_password,
                    self.settings.db_host,
                    self.settings.db_name,
                ]
            ):
                self.logger.error("Missing required database configuration")
                return False

            # Log configuration summary
            self.logger.info(
                f"Database: {self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}"
            )
            self.logger.info(
                f"Pool Size: {self.settings.db_pool_size} (max overflow: {self.settings.db_max_overflow})"
            )
            self.logger.info(f"Cache Limit: {self.settings.cache_size_limit:,} records")
            self.logger.info(
                f"CORS Origins: {len(self.settings.cors_origins)} configured"
            )

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Environment validation failed: {e}", exc_info=True)
            else:
                print(f"Environment validation failed: {e}")
            return False

    def initialize_database(self) -> bool:
        """Initialize database connection"""
        try:
            self.logger.info("Initializing database connection...")

            if not initialize_database(self.settings):
                self.logger.error("Database initialization failed")
                return False

            # Test database health
            db_manager = get_database_manager()
            health = db_manager.health_check()

            if health["status"] != "healthy":
                self.logger.error(f"Database health check failed: {health}")
                return False

            self.logger.info(
                f"Database initialized successfully (response time: {health['response_time_ms']}ms)"
            )
            return True

        except Exception as e:
            self.logger.error(f"Database initialization error: {e}", exc_info=True)
            return False

    def initialize_cache(self) -> bool:
        """Initialize application cache"""
        try:
            self.logger.info("Initializing application cache...")

            # Get database session for cache initialization
            db_manager = get_database_manager()

            with db_manager.get_session_context() as session:
                cache_start_time = time.time()

                success = cache_manager.initialize(session)

                if not success:
                    self.logger.error("Cache initialization failed")
                    return False

                cache_init_time = time.time() - cache_start_time

                # Get cache statistics
                stats = cache_manager.get_cache_stats()

                self.logger.info(
                    f"Cache initialized successfully in {cache_init_time:.2f}s"
                )
                self.logger.info(
                    f"Cached data: {stats['posts_count']} posts, {stats['users_count']} users, "
                    f"{stats['comments_count']} comments, {stats['tags_count']} tags"
                )

                # Validate cache initialization time requirement (< 5 seconds)
                if cache_init_time > 5.0:
                    self.logger.warning(
                        f"Cache initialization took {cache_init_time:.2f}s (target: < 5s)"
                    )
                else:
                    self.logger.info(
                        f"✓ Cache initialization meets performance target (< 5s)"
                    )

                return True

        except Exception as e:
            self.logger.error(f"Cache initialization error: {e}", exc_info=True)
            return False

    def run_startup_tests(self) -> bool:
        """Run startup validation tests"""
        try:
            self.logger.info("Running startup validation tests...")

            # Test 1: Database connectivity
            db_manager = get_database_manager()
            db_health = db_manager.health_check()

            if db_health["status"] != "healthy":
                self.logger.error(f"Database health test failed: {db_health}")
                return False

            self.logger.info("✓ Database connectivity test passed")

            # Test 2: Cache functionality
            if not cache_manager.is_initialized():
                self.logger.error("Cache not initialized")
                return False

            # Test cache data access
            try:
                posts = cache_manager.get_posts(skip=0, limit=1)
                users = cache_manager.get_users(skip=0, limit=1)
                self.logger.info("✓ Cache functionality test passed")
            except Exception as e:
                self.logger.error(f"Cache functionality test failed: {e}")
                return False

            # Test 3: Performance validation
            cache_stats = cache_manager.get_cache_stats()
            if cache_stats.get("initialization_time", 0) > 5.0:
                self.logger.warning("Cache initialization time exceeds target (5s)")
            else:
                self.logger.info("✓ Performance requirements met")

            return True

        except Exception as e:
            self.logger.error(f"Startup tests failed: {e}", exc_info=True)
            return False

    def startup(self) -> bool:
        """Complete application startup sequence"""
        try:
            # Setup signal handlers
            self.setup_signal_handlers()

            # Step 1: Validate environment
            if not self.validate_environment():
                return False

            # Step 2: Initialize database
            if not self.initialize_database():
                return False

            # Step 3: Initialize cache
            if not self.initialize_cache():
                return False

            # Step 4: Run startup tests
            if not self.run_startup_tests():
                return False

            # Calculate total startup time
            total_startup_time = time.time() - self.startup_time

            self.logger.info("=" * 60)
            self.logger.info("TOMOSU Backend API - Startup Complete")
            self.logger.info(f"Total startup time: {total_startup_time:.2f}s")
            self.logger.info(
                f"Ready to serve requests on {self.settings.host}:{self.settings.port}"
            )
            self.logger.info("=" * 60)

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Startup failed: {e}", exc_info=True)
            else:
                print(f"Startup failed: {e}")
            return False

    def shutdown(self):
        """Graceful application shutdown"""
        if self.logger:
            self.logger.info("Shutting down application...")

        try:
            # Close database connections
            db_manager = get_database_manager()
            db_manager.close()

            if self.logger:
                self.logger.info("Application shutdown complete")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during shutdown: {e}", exc_info=True)


def main():
    """Main startup function"""
    startup_manager = ApplicationStartup()

    try:
        # Run startup sequence
        if not startup_manager.startup():
            print("Application startup failed")
            sys.exit(1)

        # Import and run the FastAPI application
        import uvicorn
        from main import app

        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=startup_manager.settings.host,
            port=startup_manager.settings.port,
            workers=startup_manager.settings.workers,
            log_level=startup_manager.settings.log_level.value.lower(),
            access_log=True,
            use_colors=not startup_manager.settings.is_production,
            server_header=False,
            date_header=False,
        )

        server = uvicorn.Server(config)

        # Run server
        server.run()

    except KeyboardInterrupt:
        startup_manager.logger.info("Received keyboard interrupt")
    except Exception as e:
        if startup_manager.logger:
            startup_manager.logger.error(f"Application error: {e}", exc_info=True)
        else:
            print(f"Application error: {e}")
        sys.exit(1)
    finally:
        startup_manager.shutdown()


if __name__ == "__main__":
    main()
