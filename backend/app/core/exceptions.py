"""Custom exceptions for the job automation system."""

class ServiceError(Exception):
    """Base exception for service-related errors."""
    pass

class ModelNotAvailableError(ServiceError):
    """Raised when a model service is not available."""
    pass

class ApplicationError(Exception):
    """Base exception for application-related errors."""
    pass

class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

class DocumentGenerationError(ServiceError):
    """Raised when document generation fails."""
    pass
