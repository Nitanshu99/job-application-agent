"""
Logging configuration for the Job Automation System.

This module provides comprehensive logging functionality including structured logging,
file rotation, different log levels, and integration with monitoring systems.

Features:
- Structured JSON logging for production
- Console and file logging handlers
- Log rotation and archiving
- Performance monitoring and metrics
- Request/response logging
- Error tracking and alerting
- Security event logging
"""

import os
import sys
import json
import logging
import logging.handlers
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pathlib import Path
import asyncio
from contextvars import ContextVar

from app.core.config import get_settings

# Get settings
settings = get_settings()

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar('user_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log data
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_data['user_id'] = user_id
        
        # Add exception information
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info', 'taskName'
                ]:
                    try:
                        # Only include JSON serializable values
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console output."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build log message
        log_message = (
            f"{color}[{timestamp}] {record.levelname:8s}{reset} "
            f"| {record.name:20s} | {record.getMessage()}"
        )
        
        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_message += f" | req_id: {request_id[:8]}"
        
        # Add exception information
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"
        
        return log_message


class RequestFilter(logging.Filter):
    """Filter to add request context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record."""
        request_id = request_id_var.get()
        if request_id:
            record.request_id = request_id
        
        user_id = user_id_var.get()
        if user_id:
            record.user_id = user_id
        
        return True


class PerformanceLogger:
    """Logger for performance monitoring."""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
    
    def log_request_time(
        self, 
        method: str, 
        path: str, 
        duration: float, 
        status_code: int,
        user_id: Optional[int] = None
    ):
        """Log request processing time."""
        self.logger.info(
            "Request processed",
            extra={
                'event_type': 'request_processed',
                'method': method,
                'path': path,
                'duration': duration,
                'status_code': status_code,
                'user_id': user_id
            }
        )
    
    def log_database_query(
        self, 
        query_type: str, 
        duration: float, 
        table: Optional[str] = None
    ):
        """Log database query performance."""
        self.logger.info(
            "Database query executed",
            extra={
                'event_type': 'database_query',
                'query_type': query_type,
                'duration': duration,
                'table': table
            }
        )
    
    def log_llm_request(
        self, 
        model: str, 
        duration: float, 
        token_count: Optional[int] = None,
        success: bool = True
    ):
        """Log LLM service request performance."""
        self.logger.info(
            "LLM request processed",
            extra={
                'event_type': 'llm_request',
                'model': model,
                'duration': duration,
                'token_count': token_count,
                'success': success
            }
        )


class SecurityLogger:
    """Logger for security events."""
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_login_attempt(
        self, 
        email: str, 
        success: bool, 
        ip_address: str,
        user_agent: Optional[str] = None
    ):
        """Log login attempt."""
        level = logging.INFO if success else logging.WARNING
        message = "Login successful" if success else "Login failed"
        
        self.logger.log(
            level,
            message,
            extra={
                'event_type': 'login_attempt',
                'email': email,
                'success': success,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
        )
    
    def log_permission_denied(
        self, 
        user_id: int, 
        resource: str, 
        action: str,
        ip_address: str
    ):
        """Log permission denied events."""
        self.logger.warning(
            "Permission denied",
            extra={
                'event_type': 'permission_denied',
                'user_id': user_id,
                'resource': resource,
                'action': action,
                'ip_address': ip_address
            }
        )
    
    def log_suspicious_activity(
        self, 
        activity_type: str, 
        details: Dict[str, Any],
        ip_address: str,
        user_id: Optional[int] = None
    ):
        """Log suspicious security activity."""
        self.logger.error(
            f"Suspicious activity detected: {activity_type}",
            extra={
                'event_type': 'suspicious_activity',
                'activity_type': activity_type,
                'details': details,
                'ip_address': ip_address,
                'user_id': user_id
            }
        )


def setup_logging() -> None:
    """Set up logging configuration based on environment."""
    
    # Create logs directory if it doesn't exist
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    
    if settings.is_production:
        # Production: structured JSON logging
        console_formatter = StructuredFormatter()
    else:
        # Development: colored console logging
        console_formatter = ColoredConsoleFormatter()
    
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(RequestFilter())
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=settings.log_file,
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, settings.log_level))
            file_handler.setFormatter(StructuredFormatter())
            file_handler.addFilter(RequestFilter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Silence overly verbose loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.ERROR)
    
    logging.info(f"Logging initialized - Level: {settings.log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_request_context(request_id: str, user_id: Optional[int] = None) -> None:
    """
    Set request context for logging.
    
    Args:
        request_id: Unique request identifier
        user_id: User ID (if authenticated)
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """Clear request context."""
    request_id_var.set(None)
    user_id_var.set(None)


def log_function_call(func_name: str, args: tuple = (), kwargs: dict = None):
    """
    Decorator to log function calls.
    
    Args:
        func_name: Function name
        args: Function arguments
        kwargs: Function keyword arguments
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = asyncio.get_event_loop().time() if asyncio.iscoroutinefunction(func) else None
            
            logger.debug(
                f"Calling {func_name}",
                extra={
                    'function': func_name,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()) if kwargs else []
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                if start_time:
                    duration = asyncio.get_event_loop().time() - start_time
                    logger.debug(
                        f"Completed {func_name}",
                        extra={
                            'function': func_name,
                            'duration': duration,
                            'success': True
                        }
                    )
                
                return result
                
            except Exception as e:
                if start_time:
                    duration = asyncio.get_event_loop().time() - start_time
                    logger.error(
                        f"Error in {func_name}: {str(e)}",
                        extra={
                            'function': func_name,
                            'duration': duration,
                            'error': str(e),
                            'success': False
                        },
                        exc_info=True
                    )
                else:
                    logger.error(
                        f"Error in {func_name}: {str(e)}",
                        extra={
                            'function': func_name,
                            'error': str(e),
                            'success': False
                        },
                        exc_info=True
                    )
                raise
        
        return wrapper
    return decorator


class LogCapture:
    """Context manager to capture logs for testing."""
    
    def __init__(self, logger_name: str = None, level: int = logging.DEBUG):
        self.logger_name = logger_name
        self.level = level
        self.handler = None
        self.records = []
    
    def __enter__(self):
        self.handler = logging.handlers.MemoryHandler(capacity=1000)
        self.handler.setLevel(self.level)
        
        if self.logger_name:
            logger = logging.getLogger(self.logger_name)
        else:
            logger = logging.getLogger()
        
        logger.addHandler(self.handler)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            self.records = self.handler.buffer[:]
            
            if self.logger_name:
                logger = logging.getLogger(self.logger_name)
            else:
                logger = logging.getLogger()
            
            logger.removeHandler(self.handler)
    
    def get_records(self, level: int = None) -> list:
        """Get captured log records, optionally filtered by level."""
        if level is None:
            return self.records
        return [record for record in self.records if record.levelno >= level]


# Create global logger instances
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()


def log_startup_info():
    """Log application startup information."""
    logger = get_logger("startup")
    
    logger.info(
        "Application starting up",
        extra={
            'app_name': settings.app_name,
            'app_version': settings.app_version,
            'environment': settings.env,
            'debug': settings.debug,
            'log_level': settings.log_level
        }
    )


def log_shutdown_info():
    """Log application shutdown information."""
    logger = get_logger("shutdown")
    
    logger.info(
        "Application shutting down",
        extra={
            'app_name': settings.app_name,
            'environment': settings.env
        }
    )


# Initialize logging on module import
if not logging.getLogger().handlers:
    setup_logging()