"""
API v1 router configuration for the job automation system.

This module sets up all the API endpoints and their routing configuration.
"""

from fastapi import APIRouter

from app.api.v1 import auth, users, jobs, applications, documents

# Create the main API v1 router
api_router = APIRouter()

# Include all endpoint routers with their respective prefixes and tags
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        422: {"description": "Validation Error"}
    }
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "User not found"},
        422: {"description": "Validation Error"}
    }
)

api_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["jobs"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Job not found"},
        422: {"description": "Validation Error"}
    }
)

api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["applications"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Application not found"},
        422: {"description": "Validation Error"}
    }
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Document not found"},
        422: {"description": "Validation Error"}
    }
)

# API version and health check endpoints
@api_router.get("/", tags=["root"])
async def api_root():
    """
    API root endpoint providing version and service information.
    
    :return: API information
    :rtype: dict
    """
    return {
        "message": "Job Automation System API v1",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "authentication": "/api/v1/auth",
            "users": "/api/v1/users", 
            "jobs": "/api/v1/jobs",
            "applications": "/api/v1/applications",
            "documents": "/api/v1/documents"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        }
    }


@api_router.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for monitoring service status.
    
    :return: Health status information
    :rtype: dict
    """
    return {
        "status": "healthy",
        "timestamp": "2025-01-09T00:00:00Z",
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "llm_models": "available",
            "scraping_services": "active",
            "notification_service": "running"
        }
    }


# Export the main router
__all__ = ["api_router"]