"""
Pydantic schemas package for the Job Automation System.

This package contains all Pydantic schemas used for request/response validation,
serialization, and data modeling throughout the FastAPI backend.

Schemas are organized by domain:
- user: User profiles, authentication, preferences
- job: Job postings, search, matching, analytics  
- document: Document generation, templates, management
- application: Job applications, tracking, history
- auth: Authentication, tokens, sessions
- common: Shared schemas, pagination, responses
"""

# User schemas
from .user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserSummary,
    UserPasswordUpdate,
    UserPreferences,
    UserPreferencesUpdate,
    UserStats,
)

# Job schemas
from .job import (
    JobBase,
    JobCreate,
    JobUpdate,
    JobResponse,
    JobSummary,
    JobSearch,
    JobMatch,
    JobAnalytics,
    JobAlert,
    JobBulkAction,
    JobTypeEnum,
    ExperienceLevelEnum,
    JobSourceEnum,
    RemoteTypeEnum,
)

# Document schemas
from .document import (
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentSummary,
    DocumentGeneration,
    DocumentGenerationResponse,
    DocumentTemplate,
    DocumentExport,
    DocumentComparison,
    DocumentAnalytics,
    DocumentBulkAction,
    DocumentVersion,
    DocumentTypeEnum,
    TemplateStyleEnum,
    DocumentStatusEnum,
    FileFormatEnum,
)

# Define what gets exported when using "from app.schemas import *"
__all__ = [
    # User schemas
    "UserBase",
    "UserCreate", 
    "UserUpdate",
    "UserResponse",
    "UserSummary",
    "UserPasswordUpdate",
    "UserPreferences",
    "UserPreferencesUpdate",
    "UserStats",
    
    # Job schemas
    "JobBase",
    "JobCreate",
    "JobUpdate", 
    "JobResponse",
    "JobSummary",
    "JobSearch",
    "JobMatch",
    "JobAnalytics",
    "JobAlert",
    "JobBulkAction",
    "JobTypeEnum",
    "ExperienceLevelEnum",
    "JobSourceEnum",
    "RemoteTypeEnum",
    
    # Document schemas
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse", 
    "DocumentSummary",
    "DocumentGeneration",
    "DocumentGenerationResponse",
    "DocumentTemplate",
    "DocumentExport",
    "DocumentComparison",
    "DocumentAnalytics",
    "DocumentBulkAction",
    "DocumentVersion",
    "DocumentTypeEnum",
    "TemplateStyleEnum", 
    "DocumentStatusEnum",
    "FileFormatEnum",
]

# Schema collections for easy importing
USER_SCHEMAS = [
    UserBase, UserCreate, UserUpdate, UserResponse, UserSummary,
    UserPasswordUpdate, UserPreferences, UserPreferencesUpdate, UserStats
]

JOB_SCHEMAS = [
    JobBase, JobCreate, JobUpdate, JobResponse, JobSummary,
    JobSearch, JobMatch, JobAnalytics, JobAlert, JobBulkAction
]

DOCUMENT_SCHEMAS = [
    DocumentBase, DocumentCreate, DocumentUpdate, DocumentResponse, DocumentSummary,
    DocumentGeneration, DocumentGenerationResponse, DocumentTemplate, DocumentExport,
    DocumentComparison, DocumentAnalytics, DocumentBulkAction, DocumentVersion
]

# Enum collections
JOB_ENUMS = [JobTypeEnum, ExperienceLevelEnum, JobSourceEnum, RemoteTypeEnum]
DOCUMENT_ENUMS = [DocumentTypeEnum, TemplateStyleEnum, DocumentStatusEnum, FileFormatEnum]

ALL_SCHEMAS = USER_SCHEMAS + JOB_SCHEMAS + DOCUMENT_SCHEMAS
ALL_ENUMS = JOB_ENUMS + DOCUMENT_ENUMS

# Schema version for API compatibility
SCHEMA_VERSION = "1.0.0"

# Schema metadata
SCHEMA_INFO = {
    "version": SCHEMA_VERSION,
    "user_schemas": len(USER_SCHEMAS),
    "job_schemas": len(JOB_SCHEMAS), 
    "document_schemas": len(DOCUMENT_SCHEMAS),
    "total_schemas": len(ALL_SCHEMAS),
    "total_enums": len(ALL_ENUMS),
}


def get_schema_info() -> dict:
    """Get information about available schemas."""
    return SCHEMA_INFO


def get_schema_by_name(schema_name: str):
    """Get schema class by name."""
    # Create a mapping of schema names to classes
    schema_map = {}
    for schema_class in ALL_SCHEMAS:
        schema_map[schema_class.__name__] = schema_class
    
    return schema_map.get(schema_name)


def list_schemas() -> list:
    """List all available schema names."""
    return [schema.__name__ for schema in ALL_SCHEMAS]


def list_enums() -> list:
    """List all available enum names."""
    return [enum.__name__ for enum in ALL_ENUMS]


# Import validation - ensure all schemas are properly defined
def validate_schemas():
    """Validate that all schemas are properly defined and importable."""
    try:
        # Test that all schemas in __all__ are actually available
        for schema_name in __all__:
            if schema_name not in globals():
                raise ImportError(f"Schema {schema_name} not found in globals")
        
        # Test that schema collections are properly defined
        for schema in ALL_SCHEMAS:
            if not hasattr(schema, '__name__'):
                raise AttributeError(f"Schema {schema} missing __name__ attribute")
        
        return True
    except Exception as e:
        print(f"Schema validation failed: {e}")
        return False


# Run validation on import
if not validate_schemas():
    print("Warning: Schema validation failed during import")

# Convenience imports for common patterns
from typing import Union, Optional, List, Dict, Any

# Common type aliases for schemas
UserSchemaType = Union[UserCreate, UserUpdate, UserResponse]
JobSchemaType = Union[JobCreate, JobUpdate, JobResponse]  
DocumentSchemaType = Union[DocumentCreate, DocumentUpdate, DocumentResponse]

# Response wrapper types (for future use)
PaginatedResponse = Dict[str, Any]  # Will be defined in common.py when created
ErrorResponse = Dict[str, Any]      # Will be defined in common.py when created
SuccessResponse = Dict[str, Any]    # Will be defined in common.py when created