"""
SQLAlchemy models package for the Job Automation System.

This package contains all database models, enums, and utilities for the FastAPI backend.
Models are organized by domain and feature complete relationships, validation, and helper methods.

Models included:
- User: User authentication, profiles, and preferences
- Job: Job postings, scraping, and matching
- Application: Job applications with comprehensive tracking
- Document: Resume, cover letter, and document management
- ApplicationHistory: Audit trail and event tracking

Features:
- Comprehensive relationship mapping
- Duplicate prevention and detection
- Audit trails and history tracking
- AI integration support
- Version control and templating
- Advanced analytics and metrics
"""

from sqlalchemy.ext.declarative import declarative_base

# Create single Base class for all models
Base = declarative_base()

# Import all models - this ensures they are registered with SQLAlchemy
# Note: Each model file should import Base from this __init__.py file
from .user import User
from .job import Job, JobStatus, JobType, ExperienceLevel
from .application import Application, ApplicationStatus, ApplicationMethod
from .document import Document, DocumentType, DocumentFormat, DocumentStatus
from .application_history import (
    ApplicationHistory, 
    HistoryEventType, 
    HistorySource,
    DuplicateApplicationDetector
)

# Model collections for easy importing and management
CORE_MODELS = [User, Job, Application, Document, ApplicationHistory]

USER_MODELS = [User]
JOB_MODELS = [Job]
APPLICATION_MODELS = [Application, ApplicationHistory]
DOCUMENT_MODELS = [Document]

ALL_MODELS = CORE_MODELS

# Enum collections
JOB_ENUMS = [JobStatus, JobType, ExperienceLevel]
APPLICATION_ENUMS = [ApplicationStatus, ApplicationMethod]
DOCUMENT_ENUMS = [DocumentType, DocumentFormat, DocumentStatus]
HISTORY_ENUMS = [HistoryEventType, HistorySource]

ALL_ENUMS = JOB_ENUMS + APPLICATION_ENUMS + DOCUMENT_ENUMS + HISTORY_ENUMS

# Utility classes
UTILITY_CLASSES = [DuplicateApplicationDetector]

# Define what gets exported when using "from app.models import *"
__all__ = [
    # Base class
    "Base",
    
    # Core models
    "User",
    "Job", 
    "Application",
    "Document",
    "ApplicationHistory",
    
    # Job enums
    "JobStatus",
    "JobType", 
    "ExperienceLevel",
    
    # Application enums
    "ApplicationStatus",
    "ApplicationMethod",
    
    # Document enums
    "DocumentType",
    "DocumentFormat",
    "DocumentStatus",
    
    # History enums
    "HistoryEventType",
    "HistorySource",
    
    # Utility classes
    "DuplicateApplicationDetector",
    
    # Model collections
    "ALL_MODELS",
    "CORE_MODELS",
    "USER_MODELS",
    "JOB_MODELS", 
    "APPLICATION_MODELS",
    "DOCUMENT_MODELS",
    "ALL_ENUMS",
    "UTILITY_CLASSES",
]

# Model metadata for introspection and management
MODEL_INFO = {
    "version": "1.0.0",
    "total_models": len(ALL_MODELS),
    "total_enums": len(ALL_ENUMS),
    "core_models": len(CORE_MODELS),
    "utility_classes": len(UTILITY_CLASSES),
    "tables": [model.__tablename__ for model in ALL_MODELS],
}

# Relationship validation and setup
def setup_model_relationships():
    """
    Validate and configure model relationships.
    This ensures all foreign key relationships are properly established.
    """
    try:
        # Verify User relationships
        assert hasattr(User, 'jobs'), "User.jobs relationship not found"
        assert hasattr(User, 'applications'), "User.applications relationship not found"
        assert hasattr(User, 'documents'), "User.documents relationship not found"
        
        # Verify Job relationships
        assert hasattr(Job, 'user'), "Job.user relationship not found"
        assert hasattr(Job, 'applications'), "Job.applications relationship not found"
        
        # Verify Application relationships
        assert hasattr(Application, 'user'), "Application.user relationship not found"
        assert hasattr(Application, 'job'), "Application.job relationship not found"
        assert hasattr(Application, 'cover_letter'), "Application.cover_letter relationship not found"
        assert hasattr(Application, 'resume'), "Application.resume relationship not found"
        assert hasattr(Application, 'history'), "Application.history relationship not found"
        
        # Verify Document relationships
        assert hasattr(Document, 'user'), "Document.user relationship not found"
        assert hasattr(Document, 'job'), "Document.job relationship not found"
        
        # Verify ApplicationHistory relationships
        assert hasattr(ApplicationHistory, 'application'), "ApplicationHistory.application relationship not found"
        assert hasattr(ApplicationHistory, 'user'), "ApplicationHistory.user relationship not found"
        
        return True
        
    except AssertionError as e:
        print(f"Relationship validation failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during relationship validation: {e}")
        return False

def get_model_info() -> dict:
    """Get information about available models."""
    return MODEL_INFO

def get_model_by_name(model_name: str):
    """Get model class by name."""
    model_map = {
        "User": User,
        "Job": Job,
        "Application": Application, 
        "Document": Document,
        "ApplicationHistory": ApplicationHistory,
    }
    return model_map.get(model_name)

def get_enum_by_name(enum_name: str):
    """Get enum class by name."""
    enum_map = {}
    for enum_class in ALL_ENUMS:
        enum_map[enum_class.__name__] = enum_class
    return enum_map.get(enum_name)

def list_models() -> list:
    """List all available model names."""
    return [model.__name__ for model in ALL_MODELS]

def list_enums() -> list:
    """List all available enum names."""
    return [enum.__name__ for enum in ALL_ENUMS]

def list_tables() -> list:
    """List all database table names."""
    return [model.__tablename__ for model in ALL_MODELS]

def validate_models():
    """
    Validate that all models are properly defined and importable.
    Runs relationship validation and basic integrity checks.
    """
    try:
        # Check that all models in __all__ are actually available
        for model_name in ["User", "Job", "Application", "Document", "ApplicationHistory"]:
            if model_name not in globals():
                raise ImportError(f"Model {model_name} not found in globals")
        
        # Validate relationships
        if not setup_model_relationships():
            raise ValueError("Model relationship validation failed")
        
        # Check that all models have required attributes
        for model in ALL_MODELS:
            if not hasattr(model, '__tablename__'):
                raise AttributeError(f"Model {model.__name__} missing __tablename__ attribute")
            
            if not hasattr(model, '__table__'):
                raise AttributeError(f"Model {model.__name__} missing __table__ attribute")
        
        # Validate enums
        for enum_class in ALL_ENUMS:
            if not hasattr(enum_class, '__members__'):
                raise AttributeError(f"Enum {enum_class.__name__} missing __members__ attribute")
        
        return True
        
    except Exception as e:
        print(f"Model validation failed: {e}")
        return False

# Database initialization helpers
def create_all_tables(engine):
    """Create all tables using the provided engine."""
    try:
        Base.metadata.create_all(bind=engine)
        print(f"Successfully created {len(ALL_MODELS)} tables")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

def drop_all_tables(engine):
    """Drop all tables using the provided engine."""
    try:
        Base.metadata.drop_all(bind=engine)
        print(f"Successfully dropped all tables")
        return True
    except Exception as e:
        print(f"Error dropping tables: {e}")
        return False

# Model event handlers and hooks
def setup_model_events():
    """Set up SQLAlchemy event handlers for models."""
    from sqlalchemy import event
    from datetime import datetime
    
    # User model events
    @event.listens_for(User, 'before_insert')
    def set_user_defaults(mapper, connection, target):
        """Set default values for new users."""
        if not target.created_at:
            target.created_at = datetime.utcnow()
        if not target.is_active:
            target.is_active = True
    
    # Application model events  
    @event.listens_for(Application, 'before_insert')
    def set_application_defaults(mapper, connection, target):
        """Set default values for new applications."""
        if not target.created_at:
            target.created_at = datetime.utcnow()
        if not target.application_hash:
            target.application_hash = target.calculate_application_hash()
    
    # Document model events
    @event.listens_for(Document, 'before_insert') 
    def set_document_defaults(mapper, connection, target):
        """Set default values for new documents."""
        if not target.created_at:
            target.created_at = datetime.utcnow()
        if target.binary_content and not target.file_hash:
            target.file_hash = target.calculate_file_hash(target.binary_content)
    
    # ApplicationHistory model events
    @event.listens_for(ApplicationHistory, 'before_insert')
    def set_history_defaults(mapper, connection, target):
        """Set default values for new history entries.""" 
        if not target.created_at:
            target.created_at = datetime.utcnow()
        if not target.event_timestamp:
            target.event_timestamp = datetime.utcnow()
        if not target.duplicate_hash:
            target.duplicate_hash = target.calculate_event_hash()

# Run validation and setup on import
if not validate_models():
    print("Warning: Model validation failed during import")

# Setup model events
try:
    setup_model_events()
except Exception as e:
    print(f"Warning: Model event setup failed: {e}")

# Export version for compatibility checking
__version__ = MODEL_INFO["version"]