"""
Application configuration settings for the Job Automation System.

This module handles all configuration management including environment variables,
database settings, API keys, and service configurations using Pydantic Settings.

Features:
- Environment-based configuration
- Database connection settings
- Redis cache configuration
- LLM service endpoints
- Security settings
- Email and notification settings
- File upload and storage settings
"""

import os
import secrets
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

from pydantic import (
    BaseSettings, 
    PostgresDsn, 
    RedisDsn,
    validator,
    Field,
    EmailStr
)


class Settings(BaseSettings):
    """Application settings with validation and type checking."""
    
    # Application settings
    app_name: str = Field(default="Job Automation System", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    env: str = Field(default="development", env="ENVIRONMENT")
    api_v1_str: str = Field(default="/api/v1", env="API_V1_STR")
    
    # Security settings
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    password_reset_token_expire_hours: int = Field(default=24, env="PASSWORD_RESET_TOKEN_EXPIRE_HOURS")
    
    # CORS settings
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    
    # Database settings
    database_url: PostgresDsn = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis settings
    redis_url: RedisDsn = Field(env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=30, env="REDIS_SOCKET_TIMEOUT")
    redis_health_check_interval: int = Field(default=30, env="REDIS_HEALTH_CHECK_INTERVAL")
    
    # Cache settings
    cache_default_ttl: int = Field(default=3600, env="CACHE_DEFAULT_TTL")  # 1 hour
    cache_long_ttl: int = Field(default=86400, env="CACHE_LONG_TTL")      # 24 hours
    cache_short_ttl: int = Field(default=300, env="CACHE_SHORT_TTL")      # 5 minutes
    
    # LLM Service URLs
    phi3_service_url: str = Field(default="http://localhost:8001", env="PHI3_SERVICE_URL")
    gemma_service_url: str = Field(default="http://localhost:8002", env="GEMMA_SERVICE_URL")
    mistral_service_url: str = Field(default="http://localhost:8003", env="MISTRAL_SERVICE_URL")
    
    # LLM Service settings
    llm_timeout: int = Field(default=30, env="LLM_TIMEOUT")
    llm_max_retries: int = Field(default=3, env="LLM_MAX_RETRIES")
    llm_retry_delay: int = Field(default=1, env="LLM_RETRY_DELAY")
    default_llm_model: str = Field(default="phi3", env="DEFAULT_LLM_MODEL")
    
    # Job automation settings
    enable_auto_apply: bool = Field(default=False, env="ENABLE_AUTO_APPLY")
    max_applications_per_day: int = Field(default=50, env="MAX_APPLICATIONS_PER_DAY")
    application_interval_minutes: int = Field(default=10, env="APPLICATION_INTERVAL_MINUTES")
    duplicate_similarity_threshold: float = Field(default=0.85, env="DUPLICATE_SIMILARITY_THRESHOLD")
    application_history_retention_days: int = Field(default=365, env="APPLICATION_HISTORY_RETENTION_DAYS")
    
    # Web scraping settings
    scraper_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        env="SCRAPER_USER_AGENT"
    )
    scraper_delay_min: int = Field(default=1, env="SCRAPER_DELAY_MIN")
    scraper_delay_max: int = Field(default=3, env="SCRAPER_DELAY_MAX")
    scraper_timeout: int = Field(default=30, env="SCRAPER_TIMEOUT")
    scraper_max_retries: int = Field(default=3, env="SCRAPER_MAX_RETRIES")
    
    # File upload settings
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: List[str] = Field(
        default=["pdf", "doc", "docx", "txt"],
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    temp_dir: str = Field(default="temp", env="TEMP_DIR")
    
    # Email settings
    smtp_server: str = Field(default="", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    email_user: str = Field(default="", env="EMAIL_USER")
    email_password: str = Field(default="", env="EMAIL_PASSWORD")
    from_email: EmailStr = Field(default="noreply@jobautomation.com", env="FROM_EMAIL")
    
    # Notification settings
    enable_notifications: bool = Field(default=True, env="ENABLE_NOTIFICATIONS")
    notification_email_enabled: bool = Field(default=True, env="NOTIFICATION_EMAIL_ENABLED")
    daily_summary_enabled: bool = Field(default=True, env="DAILY_SUMMARY_ENABLED")
    weekly_summary_enabled: bool = Field(default=True, env="WEEKLY_SUMMARY_ENABLED")
    
    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_max_bytes: int = Field(default=10485760, env="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Monitoring and health check settings
    health_check_interval: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    
    # AWS settings (optional for file storage and backups)
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    s3_bucket: Optional[str] = Field(default=None, env="S3_BUCKET")
    
    # Rate limiting settings
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=100, env="RATE_LIMIT_BURST")
    
    # Session settings
    session_cookie_name: str = Field(default="jobautomation_session", env="SESSION_COOKIE_NAME")
    session_max_age: int = Field(default=86400, env="SESSION_MAX_AGE")  # 24 hours
    session_secure: bool = Field(default=True, env="SESSION_SECURE")
    session_httponly: bool = Field(default=True, env="SESSION_HTTPONLY")
    
    @validator("secret_key", pre=True)
    def validate_secret_key(cls, v):
        """Generate secret key if not provided."""
        if not v:
            return secrets.token_urlsafe(32)
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse comma-separated allowed hosts."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @validator("allowed_file_types", pre=True)
    def parse_allowed_file_types(cls, v):
        """Parse comma-separated file types."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",") if ext.strip()]
        return v
    
    @validator("database_url", pre=True)
    def validate_database_url(cls, v):
        """Validate and potentially modify database URL."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    @validator("redis_url", pre=True)
    def validate_redis_url(cls, v):
        """Validate Redis URL."""
        if not v:
            raise ValueError("REDIS_URL is required")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @validator("default_llm_model")
    def validate_default_llm_model(cls, v):
        """Validate default LLM model."""
        valid_models = ["phi3", "gemma", "mistral"]
        if v.lower() not in valid_models:
            raise ValueError(f"DEFAULT_LLM_MODEL must be one of: {', '.join(valid_models)}")
        return v.lower()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.env.lower() == "testing"
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary."""
        return {
            "url": str(self.database_url),
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "pool_timeout": self.database_pool_timeout,
            "pool_recycle": self.database_pool_recycle,
            "echo": self.database_echo or self.debug,
        }
    
    @property
    def redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration dictionary."""
        return {
            "url": str(self.redis_url),
            "max_connections": self.redis_max_connections,
            "socket_timeout": self.redis_socket_timeout,
            "health_check_interval": self.redis_health_check_interval,
        }
    
    @property
    def llm_services(self) -> Dict[str, str]:
        """Get LLM service URLs dictionary."""
        return {
            "phi3": self.phi3_service_url,
            "gemma": self.gemma_service_url,
            "mistral": self.mistral_service_url,
        }
    
    def get_llm_service_url(self, model_name: str) -> str:
        """Get LLM service URL for a specific model."""
        return self.llm_services.get(model_name.lower(), self.phi3_service_url)
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings instance with all configuration loaded
    """
    return Settings()


# Global settings instance
settings = get_settings()