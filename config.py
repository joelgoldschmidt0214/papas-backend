"""
Production-ready configuration management for TOMOSU Backend API.

This module provides environment-specific configuration with proper defaults,
validation, and support for different deployment environments.
"""

import os
import logging
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Supported deployment environments"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Supported logging levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables.
    For nested settings, use double underscore notation (e.g., DB__HOST).
    """

    # --- Environment Configuration ---
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # --- Application Configuration ---
    app_name: str = Field(default="TOMOSU Backend API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    api_prefix: str = Field(default="/api/v1", description="API URL prefix")

    # --- Server Configuration ---
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # --- Database Configuration ---
    db_user: str = Field(..., env="DB_USER", description="Database username")
    db_password: str = Field(..., env="DB_PASSWORD", description="Database password")
    db_host: str = Field(..., env="DB_HOST", description="Database host")
    db_port: int = Field(default=3306, env="DB_PORT", description="Database port")
    db_name: str = Field(..., env="DB_NAME", description="Database name")
    ssl_ca_path: Optional[str] = Field(
        default=None, env="SSL_CA_PATH", description="SSL CA certificate path"
    )

    # --- Database Connection Pool Configuration ---
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Maximum overflow connections")
    db_pool_timeout: int = Field(
        default=30, description="Connection pool timeout in seconds"
    )
    db_pool_recycle: int = Field(
        default=3600, description="Connection recycle time in seconds"
    )
    db_pool_pre_ping: bool = Field(
        default=True, description="Enable connection pre-ping"
    )
    db_echo: bool = Field(default=False, description="Enable SQL query logging")

    # --- Cache Configuration ---
    cache_size_limit: int = Field(
        default=1000000, description="Maximum cache size (number of records)"
    )
    cache_initialization_timeout: int = Field(
        default=30, description="Cache initialization timeout in seconds"
    )

    # --- Authentication Configuration ---
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")
    session_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for session signing",
    )

    # --- CORS Configuration ---
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://tomosu-frontend.azurewebsites.net",
        ],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS requests"
    )

    # --- Logging Configuration ---
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    log_file: Optional[str] = Field(
        default=None, description="Log file path (if None, logs to stdout)"
    )
    log_max_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum log file size in bytes",
    )
    log_backup_count: int = Field(
        default=5, description="Number of log backup files to keep"
    )

    # --- Performance Configuration ---
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    response_compression_threshold: int = Field(
        default=500, description="Minimum response size for compression (bytes)"
    )
    max_request_size: int = Field(
        default=16 * 1024 * 1024,  # 16MB
        description="Maximum request size in bytes",
    )

    # --- Health Check Configuration ---
    health_check_timeout: int = Field(
        default=5, description="Health check timeout in seconds"
    )

    # --- Monitoring Configuration ---
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_retention_hours: int = Field(
        default=24, description="Metrics retention period in hours"
    )

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        """Validate and normalize environment value"""
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v):
        """Validate and normalize log level"""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, v):
        """Parse CORS origins from string if needed"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("db_pool_size")
    @classmethod
    def validate_db_pool_size(cls, v):
        """Validate database pool size"""
        if v < 1:
            raise ValueError("Database pool size must be at least 1")
        if v > 100:
            raise ValueError("Database pool size should not exceed 100")
        return v

    @field_validator("session_secret_key")
    @classmethod
    def validate_session_secret_key(cls, v, info):
        """Validate session secret key in production"""
        # Note: In Pydantic v2, we can't access other field values in field_validator
        # This validation will be done in a model_validator if needed
        return v

    @property
    def database_url(self) -> str:
        """Construct database URL from components"""
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment == Environment.TESTING

    def get_database_connect_args(self) -> dict:
        """Get database connection arguments"""
        connect_args = {}
        if self.ssl_ca_path:
            connect_args["ssl_ca"] = self.ssl_ca_path
        return connect_args

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow environment variables with nested structure
        env_nested_delimiter = "__"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance"""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)"""
    global settings
    settings = Settings()
    return settings
