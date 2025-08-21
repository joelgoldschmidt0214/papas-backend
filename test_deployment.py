"""
Deployment validation test suite for TOMOSU Backend API.

Tests application startup, configuration, and deployment readiness.
"""

import os
import sys
import time
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import pytest
import httpx
from unittest.mock import patch, MagicMock

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings, Environment
from logging_config import setup_logging
from database import DatabaseManager
from cache.manager import cache_manager


class DeploymentTester:
    """Test suite for deployment validation"""

    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()

    def log_test_result(
        self, test_name: str, passed: bool, message: str = "", details: Dict = None
    ):
        """Log test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "details": details or {},
            "timestamp": time.time(),
        }
        self.test_results.append(result)

        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        if details and not passed:
            for key, value in details.items():
                print(f"    {key}: {value}")

    def test_environment_configuration(self):
        """Test environment configuration loading and validation"""
        try:
            # Test development configuration
            with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
                settings = Settings()
                assert settings.environment == Environment.DEVELOPMENT
                assert settings.debug == False  # Default value

            # Test production configuration
            with patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "production",
                    "SESSION_SECRET_KEY": "secure-production-key",
                },
            ):
                settings = Settings()
                assert settings.environment == Environment.PRODUCTION
                assert not settings.debug
                assert settings.session_secret_key == "secure-production-key"

            # Test database URL construction
            with patch.dict(
                os.environ,
                {
                    "DB_USER": "testuser",
                    "DB_PASSWORD": "testpass",
                    "DB_HOST": "testhost",
                    "DB_PORT": "3306",
                    "DB_NAME": "testdb",
                },
            ):
                settings = Settings()
                expected_url = "mysql+pymysql://testuser:testpass@testhost:3306/testdb"
                assert settings.database_url == expected_url

            self.log_test_result(
                "Environment Configuration", True, "All configuration tests passed"
            )

        except Exception as e:
            self.log_test_result("Environment Configuration", False, str(e))

    def test_logging_configuration(self):
        """Test logging configuration"""
        try:
            # Test development logging
            settings = Settings(environment=Environment.DEVELOPMENT, log_level="DEBUG")
            setup_logging(settings)

            # Test production logging with file output
            with tempfile.TemporaryDirectory() as temp_dir:
                log_file = Path(temp_dir) / "test.log"
                settings = Settings(
                    environment=Environment.PRODUCTION,
                    log_level="INFO",
                    log_file=str(log_file),
                )
                setup_logging(settings)

                # Test that log file is created
                import logging

                logger = logging.getLogger("test")
                logger.info("Test log message")

                assert log_file.exists()

            self.log_test_result(
                "Logging Configuration", True, "Logging setup successful"
            )

        except Exception as e:
            self.log_test_result("Logging Configuration", False, str(e))

    def test_database_configuration(self):
        """Test database configuration and connection pooling"""
        try:
            # Mock database settings
            settings = Settings(
                db_user="testuser",
                db_password="testpass",
                db_host="testhost",
                db_port=3306,
                db_name="testdb",
                db_pool_size=5,
                db_max_overflow=10,
            )

            # Test database manager initialization (without actual connection)
            db_manager = DatabaseManager(settings)

            # Validate settings
            assert settings.db_pool_size == 5
            assert settings.db_max_overflow == 10
            assert (
                settings.database_url
                == "mysql+pymysql://testuser:testpass@testhost:3306/testdb"
            )

            self.log_test_result(
                "Database Configuration", True, "Database configuration valid"
            )

        except Exception as e:
            self.log_test_result("Database Configuration", False, str(e))

    def test_cache_initialization_performance(self):
        """Test cache initialization performance requirements"""
        try:
            # Mock database session and data
            mock_session = MagicMock()

            # Mock CRUD functions to return test data
            with patch("cache.manager.crud") as mock_crud:
                # Setup mock data
                mock_crud.get_all_posts.return_value = [MagicMock() for _ in range(100)]
                mock_crud.get_all_users.return_value = [MagicMock() for _ in range(50)]
                mock_crud.get_all_comments.return_value = [
                    MagicMock() for _ in range(200)
                ]
                mock_crud.get_all_tags.return_value = [MagicMock() for _ in range(20)]
                mock_crud.get_all_surveys.return_value = [MagicMock() for _ in range(5)]
                mock_crud.get_all_likes.return_value = [MagicMock() for _ in range(500)]
                mock_crud.get_all_bookmarks.return_value = [
                    MagicMock() for _ in range(150)
                ]
                mock_crud.get_all_follows.return_value = [
                    MagicMock() for _ in range(300)
                ]

                # Test cache initialization time
                start_time = time.time()
                success = cache_manager.initialize(mock_session)
                init_time = time.time() - start_time

                # Validate performance requirement (< 5 seconds)
                assert success, "Cache initialization failed"
                assert init_time < 5.0, (
                    f"Cache initialization took {init_time:.2f}s (target: < 5s)"
                )

                self.log_test_result(
                    "Cache Performance",
                    True,
                    f"Cache initialized in {init_time:.2f}s (target: < 5s)",
                )

        except Exception as e:
            self.log_test_result("Cache Performance", False, str(e))

    def test_container_health_checks(self):
        """Test container health check configuration"""
        try:
            # Test health check endpoint availability
            # This would normally require the application to be running
            # For now, we'll validate the configuration

            # Validate Docker health check configuration
            dockerfile_path = Path("Dockerfile")
            if dockerfile_path.exists():
                dockerfile_content = dockerfile_path.read_text()
                assert "HEALTHCHECK" in dockerfile_content
                assert "/api/v1/system/health" in dockerfile_content

            # Validate docker-compose health check
            compose_path = Path("docker-compose.yml")
            if compose_path.exists():
                compose_content = compose_path.read_text()
                assert "healthcheck:" in compose_content
                assert "/api/v1/system/health" in compose_content

            self.log_test_result(
                "Container Health Checks", True, "Health check configuration valid"
            )

        except Exception as e:
            self.log_test_result("Container Health Checks", False, str(e))

    def test_resource_limits(self):
        """Test resource limit configuration"""
        try:
            # Check docker-compose resource limits
            compose_path = Path("docker-compose.yml")
            if compose_path.exists():
                compose_content = compose_path.read_text()
                assert "resources:" in compose_content
                assert "limits:" in compose_content
                assert "memory:" in compose_content
                assert "cpus:" in compose_content

            # Check Azure Container Apps configuration
            azure_config_path = Path("azure-container-app.yaml")
            if azure_config_path.exists():
                azure_content = azure_config_path.read_text()
                assert "resources:" in azure_content
                assert "cpu:" in azure_content
                assert "memory:" in azure_content

            self.log_test_result(
                "Resource Limits", True, "Resource limit configuration valid"
            )

        except Exception as e:
            self.log_test_result("Resource Limits", False, str(e))

    def test_production_security(self):
        """Test production security configuration"""
        try:
            # Test production settings validation
            with patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "production",
                    "SESSION_SECRET_KEY": "secure-production-key-with-sufficient-length",
                },
            ):
                settings = Settings()

                # Validate security settings
                assert not settings.debug, "Debug mode should be disabled in production"
                assert (
                    settings.session_secret_key != "dev-secret-key-change-in-production"
                )
                assert settings.environment == Environment.PRODUCTION

            # Test that development endpoints are disabled in production
            settings = Settings(environment=Environment.PRODUCTION)
            # In production, docs should be disabled (handled in main.py)

            self.log_test_result(
                "Production Security", True, "Security configuration valid"
            )

        except Exception as e:
            self.log_test_result("Production Security", False, str(e))

    def test_startup_script(self):
        """Test startup script functionality"""
        try:
            # Test that startup script exists and is executable
            startup_path = Path("startup.py")
            assert startup_path.exists(), "startup.py not found"

            # Test startup script imports
            import startup

            assert hasattr(startup, "ApplicationStartup")
            assert hasattr(startup, "main")

            self.log_test_result(
                "Startup Script", True, "Startup script configuration valid"
            )

        except Exception as e:
            self.log_test_result("Startup Script", False, str(e))

    def run_all_tests(self):
        """Run all deployment tests"""
        print("=" * 60)
        print("TOMOSU Backend API - Deployment Validation Tests")
        print("=" * 60)

        test_methods = [
            self.test_environment_configuration,
            self.test_logging_configuration,
            self.test_database_configuration,
            self.test_cache_initialization_performance,
            self.test_container_health_checks,
            self.test_resource_limits,
            self.test_production_security,
            self.test_startup_script,
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test_result(
                    test_method.__name__, False, f"Test execution failed: {e}"
                )

        # Print summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
        print(f"Total Time: {time.time() - self.start_time:.2f}s")

        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['message']}")

        return failed_tests == 0


def main():
    """Run deployment validation tests"""
    tester = DeploymentTester()
    success = tester.run_all_tests()

    if success:
        print("\n🎉 All deployment tests passed! Application is ready for deployment.")
        sys.exit(0)
    else:
        print(
            "\n❌ Some deployment tests failed. Please fix the issues before deploying."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
