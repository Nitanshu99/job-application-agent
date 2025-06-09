"""
API Package for Job Automation System

This package contains all REST API endpoints, route handlers, and API-related functionality.
It follows RESTful conventions and provides comprehensive OpenAPI documentation.

API Structure:
- v1/: Version 1 API endpoints
  - auth.py: Authentication and authorization
  - users.py: User management and profiles  
  - jobs.py: Job search, matching, and management
  - applications.py: Job application tracking and automation
  - documents.py: Resume and cover letter generation

Features:
- Automatic OpenAPI/Swagger documentation
- Request/response validation with Pydantic
- JWT-based authentication and authorization
- Rate limiting and security middleware
- Comprehensive error handling
- API versioning support
- CORS configuration for frontend integration

Usage:
    from app.api.v1 import api_router
    from app.api.dependencies import get_current_user
"""

from fastapi import APIRouter
from app.api.v1 import api_router as v1_router

# Main API router that includes all versions
api_router = APIRouter()

# Include versioned routers
api_router.include_router(
    v1_router,
    prefix="/v1",
    tags=["v1"]
)

# API metadata
API_VERSION = "1.0.0"
API_TITLE = "Job Automation System API"
API_DESCRIPTION = """
## AI-Powered Job Application Automation API

This API provides comprehensive functionality for automating job applications using AI:

### 🤖 AI Services
- **Document Generation**: Create personalized resumes and cover letters using Phi-3 Mini
- **Job Matching**: Intelligent job matching and relevance scoring using Gemma 7B
- **Application Automation**: Automated form filling and submissions using Mistral 7B

### 📊 Core Features
- **User Management**: Profile creation, authentication, and preferences
- **Job Search**: Multi-source job scraping and search functionality  
- **Application Tracking**: Comprehensive application history and analytics
- **Document Management**: Template-based document generation and storage
- **Notification System**: Real-time updates and alerts

### 🔒 Security
- JWT token-based authentication
- Rate limiting and abuse prevention
- Input validation and sanitization
- CORS configuration for web clients

### 📚 Documentation
- Interactive API documentation available at `/docs`
- ReDoc documentation available at `/redoc`
- OpenAPI specification available at `/openapi.json`
"""

# Error response schemas
ERROR_RESPONSES = {
    400: {"description": "Bad Request - Invalid input parameters"},
    401: {"description": "Unauthorized - Authentication required"},
    403: {"description": "Forbidden - Insufficient permissions"},
    404: {"description": "Not Found - Resource does not exist"},
    422: {"description": "Validation Error - Invalid request data"},
    429: {"description": "Too Many Requests - Rate limit exceeded"},
    500: {"description": "Internal Server Error - Server malfunction"},
    503: {"description": "Service Unavailable - External service failure"}
}

# Export main router and metadata
__all__ = [
    "api_router",
    "API_VERSION",
    "API_TITLE", 
    "API_DESCRIPTION",
    "ERROR_RESPONSES"
]