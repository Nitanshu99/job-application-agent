"""
Application configuration settings for the Job Automation System.

This module handles all configuration management including environment variables,
database settings, API keys, and service configurations using Pydantic Settings.
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
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
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
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/jobautomation", env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=30, env="REDIS_SOCKET_TIMEOUT")
    redis_health_check_interval: int = Field(default=30, env="REDIS_HEALTH_CHECK_INTERVAL")
    
    # LLM Service settings
    phi3_service_url: str = Field(default="http://localhost:8001", env="PHI3_SERVICE_URL")
    gemma_service_url: str = Field(default="http://localhost:8002", env="GEMMA_SERVICE_URL")
    mistral_service_url: str = Field(default="http://localhost:8003", env="MISTRAL_SERVICE_URL")
    default_llm_model: str = Field(default="phi3", env="DEFAULT_LLM_MODEL")
    llm_request_timeout: int = Field(default=120, env="LLM_REQUEST_TIMEOUT")
    
    # File upload settings
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    allowed_file_types: List[str] = Field(default=[".pdf", ".doc", ".docx", ".txt"], env="ALLOWED_FILE_TYPES")
    
    # Email settings (optional)
    smtp_server: Optional[str] = Field(default=None, env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    from_email: Optional[EmailStr] = Field(default=None, env="FROM_EMAIL")
    
    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    
    # Job scraping settings
    scraping_delay: float = Field(default=1.0, env="SCRAPING_DELAY")
    max_jobs_per_search: int = Field(default=100, env="MAX_JOBS_PER_SEARCH")
    user_agent: str = Field(default="JobAutomationBot/1.0", env="USER_AGENT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
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
            "url": self.database_url,
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
            "url": self.redis_url,
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
