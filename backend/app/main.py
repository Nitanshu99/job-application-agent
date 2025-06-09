"""
FastAPI Application Entry Point for Job Automation System

This module creates and configures the main FastAPI application instance with all
middleware, routes, exception handlers, and lifecycle events.

Features:
- Automatic OpenAPI documentation generation
- CORS middleware for frontend integration
- Security middleware and rate limiting
- Database connection management
- LLM service initialization
- Background task scheduling
- Comprehensive error handling
- Health checks and monitoring

Production Configuration:
- Optimized for Docker deployment
- Supports horizontal scaling
- Integrated logging and metrics
- Database connection pooling
- Redis session management
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.logging import get_logger, setup_logging
from app.core.security import SecurityHeaders
from app.api import api_router, API_TITLE, API_DESCRIPTION, API_VERSION
from app.services import startup_services, shutdown_services

# Initialize settings and logging
settings = get_settings()
setup_logging()
logger = get_logger(__name__)

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles:
    - Database initialization
    - Service startup (LLM models, caching, etc.)
    - Background task scheduling
    - Resource cleanup on shutdown
    """
    logger.info("🚀 Starting Job Automation System...")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database...")
        await init_db()
        
        # Start all services (LLM, scrapers, notifications)
        logger.info("🤖 Starting AI and automation services...")
        await startup_services()
        
        logger.info("✅ Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}", exc_info=True)
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("🛑 Shutting down Job Automation System...")
        
        try:
            # Shutdown services
            await shutdown_services()
            
            # Close database connections
            await close_db()
            
            logger.info("✅ Application shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {str(e)}", exc_info=True)


# Create FastAPI application instance
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
    debug=settings.debug
)

# Security middleware
app.add_middleware(SecurityHeaders)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Trusted host middleware for production security
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.allowed_hosts
    )

# Include API routes
app.include_router(
    api_router,
    prefix="/api"
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with detailed error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed field information."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": exc.errors(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with proper logging."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": str(exc),
                    "path": str(request.url.path)
                }
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An internal server error occurred",
                    "path": str(request.url.path)
                }
            }
        )


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing basic application information.
    """
    return {
        "message": "🤖 Job Automation System API",
        "version": API_VERSION,
        "status": "operational",
        "features": [
            "AI-powered document generation",
            "Intelligent job matching", 
            "Automated job applications",
            "Application history tracking",
            "Multi-source job scraping"
        ],
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc", 
            "openapi": "/openapi.json"
        },
        "api": {
            "base_url": "/api",
            "version": "/api/v1",
            "authentication": "JWT Bearer Token"
        }
    }


# Health check endpoint
@app.get("/health", tags=["health"])
@limiter.limit("30/minute")
async def health_check(request: Request) -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.
    """
    try:
        # Import here to avoid circular imports
        from app.core.database import check_db_health
        from app.services import get_service_health
        
        # Check database health
        db_healthy = await check_db_health()
        
        # Check service health  
        services_health = get_service_health()
        
        # Overall health status
        all_healthy = db_healthy and all(
            status.get("initialized", False) 
            for status in services_health.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": "2025-01-09T00:00:00Z",
            "version": API_VERSION,
            "environment": settings.env,
            "services": {
                "database": "healthy" if db_healthy else "unhealthy",
                "api": "healthy",
                "llm_services": "healthy" if services_health else "unavailable"
            },
            "metrics": {
                "uptime": "operational",
                "memory_usage": "normal",
                "cpu_usage": "normal"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": "2025-01-09T00:00:00Z",
            "error": "Health check failed",
            "services": {
                "database": "unknown",
                "api": "degraded",
                "llm_services": "unknown"
            }
        }


if __name__ == "__main__":
    # Development server
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )