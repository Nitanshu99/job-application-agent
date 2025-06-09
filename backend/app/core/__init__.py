"""
Core module initialization for the Job Automation System.

This module provides access to all core functionality including configuration,
security, database, and logging components.

Usage:
    from app.core import get_settings, get_db, setup_logging
    from app.core.security import create_access_token, verify_password
    from app.core.database import DatabaseManager, get_db_session
"""

from .config import (
    Settings,
    get_settings,
    settings
)

from .security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    verify_token,
    verify_password_reset_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
    create_csrf_token,
    verify_csrf_token,
    create_signature,
    verify_signature,
    check_password_strength,
    generate_secure_filename,
    sanitize_filename,
    mask_sensitive_data,
    get_client_ip,
    generate_session_id,
    SecurityHeaders,
    constant_time_compare,
    rate_limit_key,
    oauth2_scheme,
    bearer_scheme,
    pwd_context
)

from .database import (
    Base,
    DatabaseManager,
    db_manager,
    get_db,
    get_db_session,
    get_db_transaction,
    init_db,
    close_db,
    reset_db,
    check_db_health,
    get_db_info,
    DatabaseService,
    paginate_query,
    count_query_results,
    on_startup as db_startup,
    on_shutdown as db_shutdown
)

from .logging import (
    setup_logging,
    get_logger,
    set_request_context,
    clear_request_context,
    log_function_call,
    LogCapture,
    StructuredFormatter,
    ColoredConsoleFormatter,
    RequestFilter,
    PerformanceLogger,
    SecurityLogger,
    performance_logger,
    security_logger,
    log_startup_info,
    log_shutdown_info,
    request_id_var,
    user_id_var
)

# Version information
__version__ = "1.0.0"
__author__ = "Job Automation System"
__description__ = "Core infrastructure components for the job automation system"

# Package metadata
__all__ = [
    # Configuration
    "Settings",
    "get_settings", 
    "settings",
    
    # Security
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token", 
    "create_password_reset_token",
    "verify_token",
    "verify_password_reset_token",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "create_csrf_token",
    "verify_csrf_token",
    "create_signature",
    "verify_signature",
    "check_password_strength",
    "generate_secure_filename",
    "sanitize_filename",
    "mask_sensitive_data",
    "get_client_ip",
    "generate_session_id",
    "SecurityHeaders",
    "constant_time_compare",
    "rate_limit_key",
    "oauth2_scheme",
    "bearer_scheme",
    "pwd_context",
    
    # Database
    "Base",
    "DatabaseManager",
    "db_manager",
    "get_db",
    "get_db_session",
    "get_db_transaction", 
    "init_db",
    "close_db",
    "reset_db",
    "check_db_health",
    "get_db_info",
    "DatabaseService",
    "paginate_query",
    "count_query_results",
    "db_startup",
    "db_shutdown",
    
    # Logging
    "setup_logging",
    "get_logger",
    "set_request_context",
    "clear_request_context",
    "log_function_call",
    "LogCapture",
    "StructuredFormatter",
    "ColoredConsoleFormatter", 
    "RequestFilter",
    "PerformanceLogger",
    "SecurityLogger",
    "performance_logger",
    "security_logger",
    "log_startup_info",
    "log_shutdown_info",
    "request_id_var",
    "user_id_var"
]


def initialize_core() -> None:
    """
    Initialize all core components.
    
    This function sets up logging and prepares the core infrastructure
    for the application startup.
    """
    # Setup logging first
    setup_logging()
    
    # Log core initialization
    logger = get_logger(__name__)
    logger.info(
        "Core module initialized", 
        extra={
            "module": __name__,
            "version": __version__,
            "components": ["config", "security", "database", "logging"]
        }
    )


async def startup_core() -> None:
    """
    Async startup function for core components.
    
    This function should be called during application startup to initialize
    async components like database connections.
    """
    logger = get_logger(__name__)
    
    try:
        # Initialize database
        await init_db()
        
        # Log successful startup
        log_startup_info()
        logger.info("Core components started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start core components: {e}", exc_info=True)
        raise


async def shutdown_core() -> None:
    """
    Async shutdown function for core components.
    
    This function should be called during application shutdown to properly
    close async resources like database connections.
    """
    logger = get_logger(__name__)
    
    try:
        # Close database connections
        await close_db()
        
        # Log shutdown
        log_shutdown_info()
        logger.info("Core components shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during core shutdown: {e}", exc_info=True)


def get_core_info() -> dict:
    """
    Get information about core module components.
    
    Returns:
        Dictionary with core module information
    """
    return {
        "version": __version__,
        "description": __description__, 
        "components": {
            "config": {
                "description": "Application configuration management",
                "key_functions": ["get_settings", "Settings"]
            },
            "security": {
                "description": "Authentication and security utilities", 
                "key_functions": ["create_access_token", "verify_password", "generate_api_key"]
            },
            "database": {
                "description": "Database connection and session management",
                "key_functions": ["get_db", "init_db", "DatabaseManager"]
            },
            "logging": {
                "description": "Structured logging and monitoring",
                "key_functions": ["setup_logging", "get_logger", "PerformanceLogger"]
            }
        },
        "settings": {
            "environment": settings.env,
            "debug": settings.debug,
            "app_name": settings.app_name,
            "app_version": settings.app_version
        }
    }


# Core initialization shortcuts
async def quick_init() -> None:
    """
    Quick initialization for development/testing.
    
    Initializes core components with minimal setup for rapid development.
    """
    initialize_core()
    await startup_core()


def health_check() -> dict:
    """
    Basic health check for core components.
    
    Returns:
        Dictionary with health status of core components
    """
    status = {
        "core": "healthy",
        "config": "healthy" if settings else "unhealthy",
        "logging": "healthy",
        "database": "unknown",  # Will be updated by async health check
        "timestamp": get_logger(__name__).handlers[0].format(
            get_logger(__name__).makeRecord(
                name=__name__,
                level=20,
                fn="",
                lno=0,
                msg="",
                args=(),
                exc_info=None
            )
        ) if get_logger(__name__).handlers else None
    }
    
    return status


# Initialize core on import (sync components only)
initialize_core()