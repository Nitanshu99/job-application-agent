"""
Services package for job automation system.

This package contains business logic services that handle core functionality:
- Document generation using AI models
- Job matching and parsing
- Application automation and management
- Notification systems
- Application history tracking

Usage:
    from app.services import (
        DocumentService,
        JobService,
        ApplicationService,
        ApplicationManager,
        NotificationService
    )
    
    # Initialize services
    document_service = DocumentService()
    job_service = JobService()
    application_service = ApplicationService()
    application_manager = ApplicationManager()
    notification_service = NotificationService()
"""

import logging
from typing import Dict, Any, Optional
import asyncio

# Import main service classes
from .document_service import DocumentService
from .job_service import JobService
from .application_service import ApplicationService
from .application_manager import ApplicationManager
from .notification_service import NotificationService

# Import LLM services (sub-packages)
try:
    from .llm.phi3_service import Phi3Service
    from .llm.gemma_service import GemmaService
    from .llm.mistral_service import MistralService
    from .llm.model_manager import ModelManager
except ImportError:
    # LLM services might not be available in all environments
    Phi3Service = None
    GemmaService = None
    MistralService = None
    ModelManager = None

# Import scraper services (sub-packages)
try:
    from .scrapers.base_scraper import BaseScraper
    from .scrapers.linkedin_scraper import LinkedInScraper
    from .scrapers.indeed_scraper import IndeedScraper
    from .scrapers.custom_scraper import CustomScraper
    from .scrapers.scraper_factory import ScraperFactory
except ImportError:
    # Scraper services might not be available in all environments
    BaseScraper = None
    LinkedInScraper = None
    IndeedScraper = None
    CustomScraper = None
    ScraperFactory = None

logger = logging.getLogger(__name__)

# Package metadata
__version__ = "1.0.0"
__author__ = "Job Automation System"
__description__ = "Business logic services for AI-powered job automation"

# Export main service classes
__all__ = [
    # Main services
    "DocumentService",
    "JobService", 
    "ApplicationService",
    "ApplicationManager",
    "NotificationService",
    
    # LLM services (if available)
    "Phi3Service",
    "GemmaService", 
    "MistralService",
    "ModelManager",
    
    # Scraper services (if available)
    "BaseScraper",
    "LinkedInScraper",
    "IndeedScraper",
    "CustomScraper",
    "ScraperFactory",
    
    # Utility functions
    "get_service_instance",
    "initialize_all_services",
    "get_service_health",
    "ServiceContainer"
]


class ServiceContainer:
    """
    Container for managing service instances and dependencies.
    
    This class provides a centralized way to manage service instances,
    handle dependency injection, and ensure proper service lifecycle management.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized: Dict[str, bool] = {}
        
    def register_service(self, name: str, service_class: type, **kwargs) -> None:
        """
        Register a service class with the container.
        
        Args:
            name: Service name for lookup
            service_class: Service class to instantiate
            **kwargs: Additional arguments for service initialization
        """
        self._services[name] = {
            "class": service_class,
            "instance": None,
            "kwargs": kwargs,
            "initialized": False
        }
        
    def get_service(self, name: str) -> Any:
        """
        Get a service instance, creating it if necessary.
        
        Args:
            name: Name of the service
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        service_info = self._services[name]
        
        if service_info["instance"] is None:
            service_info["instance"] = service_info["class"](**service_info["kwargs"])
            
        return service_info["instance"]
    
    async def initialize_service(self, name: str) -> bool:
        """
        Initialize a service if it has an async initialize method.
        
        Args:
            name: Name of the service
            
        Returns:
            True if initialization was successful
        """
        try:
            service = self.get_service(name)
            
            if hasattr(service, 'initialize') and callable(getattr(service, 'initialize')):
                await service.initialize()
                self._services[name]["initialized"] = True
                logger.info(f"Service '{name}' initialized successfully")
                return True
            else:
                # Service doesn't need initialization
                self._services[name]["initialized"] = True
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize service '{name}': {str(e)}")
            return False
    
    async def initialize_all_services(self) -> Dict[str, bool]:
        """
        Initialize all registered services.
        
        Returns:
            Dictionary with service names and their initialization status
        """
        results = {}
        
        for service_name in self._services.keys():
            results[service_name] = await self.initialize_service(service_name)
            
        return results
    
    def get_service_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status of all services.
        
        Returns:
            Dictionary with service health information
        """
        health_status = {}
        
        for service_name, service_info in self._services.items():
            health_status[service_name] = {
                "registered": True,
                "instantiated": service_info["instance"] is not None,
                "initialized": service_info.get("initialized", False),
                "class": service_info["class"].__name__
            }
            
            # Check if service has a health check method
            if service_info["instance"] and hasattr(service_info["instance"], 'health_check'):
                try:
                    health_status[service_name]["health_check"] = service_info["instance"].health_check()
                except Exception as e:
                    health_status[service_name]["health_check"] = f"Error: {str(e)}"
            
        return health_status
    
    def list_services(self) -> list:
        """List all registered service names."""
        return list(self._services.keys())


# Global service container instance
_service_container = ServiceContainer()


def get_service_instance(service_name: str) -> Any:
    """
    Get a service instance from the global container.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Service instance
        
    Example:
        document_service = get_service_instance("document")
        job_service = get_service_instance("job")
    """
    return _service_container.get_service(service_name)


async def initialize_all_services() -> Dict[str, bool]:
    """
    Initialize all services in the container.
    
    Returns:
        Dictionary with initialization results for each service
        
    Example:
        results = await initialize_all_services()
        if all(results.values()):
            print("All services initialized successfully")
    """
    return await _service_container.initialize_all_services()


def get_service_health() -> Dict[str, Dict[str, Any]]:
    """
    Get health status of all services.
    
    Returns:
        Dictionary with health information for each service
        
    Example:
        health = get_service_health()
        for service, status in health.items():
            print(f"{service}: {'OK' if status['initialized'] else 'NOT OK'}")
    """
    return _service_container.get_service_health()


def register_default_services() -> None:
    """Register default services with the container."""
    # Register main services
    _service_container.register_service("document", DocumentService)
    _service_container.register_service("job", JobService)
    _service_container.register_service("application", ApplicationService)
    _service_container.register_service("application_manager", ApplicationManager)
    _service_container.register_service("notification", NotificationService)
    
    # Register LLM services if available
    if Phi3Service:
        _service_container.register_service("phi3", Phi3Service)
    if GemmaService:
        _service_container.register_service("gemma", GemmaService)
    if MistralService:
        _service_container.register_service("mistral", MistralService)
    if ModelManager:
        _service_container.register_service("model_manager", ModelManager)
    
    # Register scraper services if available
    if ScraperFactory:
        _service_container.register_service("scraper_factory", ScraperFactory)
    if LinkedInScraper:
        _service_container.register_service("linkedin_scraper", LinkedInScraper)
    if IndeedScraper:
        _service_container.register_service("indeed_scraper", IndeedScraper)
    if CustomScraper:
        _service_container.register_service("custom_scraper", CustomScraper)


# Helper functions for common service combinations
async def get_document_generation_pipeline():
    """
    Get services needed for document generation pipeline.
    
    Returns:
        Tuple of (DocumentService, Phi3Service) if available
    """
    document_service = get_service_instance("document")
    phi3_service = None
    
    try:
        phi3_service = get_service_instance("phi3")
    except ValueError:
        logger.warning("Phi3Service not available for document generation")
    
    return document_service, phi3_service


async def get_job_analysis_pipeline():
    """
    Get services needed for job analysis pipeline.
    
    Returns:
        Tuple of (JobService, GemmaService) if available
    """
    job_service = get_service_instance("job")
    gemma_service = None
    
    try:
        gemma_service = get_service_instance("gemma")
    except ValueError:
        logger.warning("GemmaService not available for job analysis")
    
    return job_service, gemma_service


async def get_application_automation_pipeline():
    """
    Get services needed for application automation pipeline.
    
    Returns:
        Tuple of (ApplicationService, MistralService, ApplicationManager) if available
    """
    application_service = get_service_instance("application")
    application_manager = get_service_instance("application_manager")
    mistral_service = None
    
    try:
        mistral_service = get_service_instance("mistral")
    except ValueError:
        logger.warning("MistralService not available for application automation")
    
    return application_service, mistral_service, application_manager


# Service lifecycle management
async def startup_services():
    """
    Startup routine for all services.
    Should be called during application startup.
    """
    logger.info("Starting up job automation services...")
    
    # Register default services
    register_default_services()
    
    # Initialize all services
    initialization_results = await initialize_all_services()
    
    # Log initialization results
    successful_services = [name for name, success in initialization_results.items() if success]
    failed_services = [name for name, success in initialization_results.items() if not success]
    
    logger.info(f"Successfully initialized services: {successful_services}")
    
    if failed_services:
        logger.warning(f"Failed to initialize services: {failed_services}")
    
    return initialization_results


async def shutdown_services():
    """
    Shutdown routine for all services.
    Should be called during application shutdown.
    """
    logger.info("Shutting down job automation services...")
    
    # Get all service instances and call shutdown if available
    for service_name in _service_container.list_services():
        try:
            service = _service_container.get_service(service_name)
            
            if hasattr(service, 'shutdown') and callable(getattr(service, 'shutdown')):
                await service.shutdown()
                logger.info(f"Service '{service_name}' shutdown completed")
                
        except Exception as e:
            logger.error(f"Error shutting down service '{service_name}': {str(e)}")
    
    logger.info("Service shutdown completed")


# Convenience imports for common patterns
def create_service_bundle():
    """
    Create a bundle of commonly used services.
    
    Returns:
        Dictionary with service instances
    """
    return {
        "document": get_service_instance("document"),
        "job": get_service_instance("job"),
        "application": get_service_instance("application"),
        "application_manager": get_service_instance("application_manager"),
        "notification": get_service_instance("notification")
    }


# Development and testing utilities
def reset_service_container():
    """Reset the service container (useful for testing)."""
    global _service_container
    _service_container = ServiceContainer()


def mock_service(service_name: str, mock_instance: Any):
    """
    Replace a service with a mock instance (useful for testing).
    
    Args:
        service_name: Name of the service to mock
        mock_instance: Mock instance to use
    """
    if service_name in _service_container._services:
        _service_container._services[service_name]["instance"] = mock_instance
    else:
        # Register new mock service
        _service_container.register_service(service_name, type(mock_instance))
        _service_container._services[service_name]["instance"] = mock_instance


# Package initialization
logger.info(f"Job automation services package loaded (version {__version__})")

# Auto-register services when package is imported
register_default_services()