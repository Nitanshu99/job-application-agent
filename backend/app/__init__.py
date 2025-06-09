"""
Job Automation System - Main Application Package

This package contains the FastAPI backend application for the AI-powered job automation system.
It provides APIs for document generation, job matching, application automation, and user management.

Key Features:
- AI-powered resume and cover letter generation using Phi-3 Mini
- Intelligent job matching and parsing using Gemma 7B  
- Automated job applications using Mistral 7B Instruct
- Comprehensive user profile and application management
- Job scraping from multiple sources (LinkedIn, Indeed, custom portals)
- Application history tracking and duplicate prevention
- Document templates and customization
- Real-time notifications and analytics

Architecture:
- FastAPI with async/await support
- SQLAlchemy ORM with PostgreSQL database
- Redis for caching and session management
- Celery for background tasks
- Pydantic for data validation
- Alembic for database migrations
- Docker containerization

Package Structure:
- api/: REST API endpoints and route handlers
- core/: Core infrastructure (config, security, database, logging)
- models/: SQLAlchemy database models and relationships
- schemas/: Pydantic schemas for request/response validation
- services/: Business logic services and integrations
- utils/: Utility functions and helpers
- templates/: Document generation templates

Usage:
    from app.main import app
    from app.core import get_settings, get_db
    from app.services import DocumentService, JobService
"""

# Package metadata
__version__ = "1.0.0"
__title__ = "Job Automation System"
__description__ = "AI-powered job application automation platform"
__author__ = "Job Automation Team"
__license__ = "MIT"

# Core imports for package-level access
from app.core.config import get_settings
from app.core.database import get_db

# Version compatibility check
import sys
if sys.version_info < (3, 12):
    raise RuntimeError("Python 3.12 or higher is required")

# Package-level configuration
settings = get_settings()

# Initialize logging when package is imported
from app.core.logging import setup_logging
setup_logging()

# Export commonly used items
__all__ = [
    "__version__",
    "__title__", 
    "__description__",
    "__author__",
    "__license__",
    "get_settings",
    "get_db",
    "settings"
]