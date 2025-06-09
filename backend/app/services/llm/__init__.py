"""
LLM services package for AI-powered job automation system.

This package contains the LLM service integrations for document generation,
job analysis, and application automation using Phi-3 Mini, Gemma 7B, and
Mistral 7B models respectively.

The services are designed to work sequentially to optimize resource usage
on memory-constrained environments like MacBook Air M4 (8GB RAM).

Usage:
    from app.services.llm import ModelManager, Phi3Service, GemmaService, MistralService
    
    # Initialize the model manager
    manager = ModelManager()
    await manager.initialize()
    
    # Execute complete workflow
    result = await manager.execute_complete_workflow(user_profile, job_data)
    
    # Or use individual services
    phi3 = Phi3Service()
    await phi3.initialize()
    resume = await phi3.generate_resume(user_profile, job_data)
"""

import logging
from typing import Dict, Any, Optional, List

# Import main service classes
try:
    from .phi3_service import Phi3Service
    from .gemma_service import GemmaService, JobMatchResult
    from .mistral_service import MistralService, ApplicationResult, ApplicationStatus, FormField
    from .model_manager import ModelManager, ModelStatus, WorkflowStep
except ImportError as e:
    logging.warning(f"Failed to import LLM services: {e}")
    # Set to None if imports fail (services might not be available in all environments)
    Phi3Service = None
    GemmaService = None
    MistralService = None
    ModelManager = None
    JobMatchResult = None
    ApplicationResult = None
    ApplicationStatus = None
    FormField = None
    ModelStatus = None
    WorkflowStep = None

logger = logging.getLogger(__name__)

# Package metadata
__version__ = "1.0.0"
__author__ = "Job Automation System"
__description__ = "LLM service integrations for AI-powered job automation"

# Export main classes and types
__all__ = [
    # Main service classes
    "Phi3Service",
    "GemmaService", 
    "MistralService",
    "ModelManager",
    
    # Data classes and enums
    "JobMatchResult",
    "ApplicationResult", 
    "ApplicationStatus",
    "FormField",
    "ModelStatus",
    "WorkflowStep",
    
    # Utility functions
    "create_model_manager",
    "get_service_health",
    "check_llm_availability",
    "LLMServiceContainer"
]


class LLMServiceContainer:
    """
    Container for managing LLM service instances and dependencies.
    
    This class provides a centralized way to manage LLM service instances,
    handle initialization, and ensure proper service lifecycle management.
    """
    
    def __init__(self):
        self._model_manager = None
        self._phi3_service = None
        self._gemma_service = None
        self._mistral_service = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize all LLM services.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if ModelManager is None:
                logger.error("LLM services not available - check dependencies")
                return False
            
            # Initialize model manager (this will manage individual services)
            self._model_manager = ModelManager()
            initialization_success = await self._model_manager.initialize()
            
            if initialization_success:
                self._initialized = True
                logger.info("LLM Service Container initialized successfully")
                return True
            else:
                logger.error("Failed to initialize LLM Service Container")
                return False
                
        except Exception as e:
            logger.error(f"LLM Service Container initialization failed: {str(e)}")
            return False
    
    def get_model_manager(self) -> Optional[ModelManager]:
        """Get the model manager instance."""
        return self._model_manager
    
    def get_phi3_service(self) -> Optional[Phi3Service]:
        """Get the Phi-3 service instance."""
        if self._model_manager:
            return self._model_manager.phi3_service
        return None
    
    def get_gemma_service(self) -> Optional[GemmaService]:
        """Get the Gemma service instance."""
        if self._model_manager:
            return self._model_manager.gemma_service
        return None
    
    def get_mistral_service(self) -> Optional[MistralService]:
        """Get the Mistral service instance."""
        if self._model_manager:
            return self._model_manager.mistral_service
        return None
    
    async def execute_workflow(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        workflow_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete job application workflow.
        
        Args:
            user_profile: User's professional profile
            job_data: Job posting information
            workflow_config: Optional workflow configuration
            
        Returns:
            Complete workflow results
        """
        if not self._initialized or not self._model_manager:
            raise RuntimeError("LLM Service Container not initialized")
        
        return await self._model_manager.execute_complete_workflow(
            user_profile, job_data, workflow_config
        )
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get health status of all LLM services.
        
        Returns:
            Health status for all services
        """
        if not self._initialized or not self._model_manager:
            return {
                "container_initialized": False,
                "error": "Service container not initialized"
            }
        
        health_status = await self._model_manager.check_all_services_health()
        health_status["container_initialized"] = True
        return health_status
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage statistics.
        
        Returns:
            Resource usage information
        """
        if not self._initialized or not self._model_manager:
            return {"error": "Service container not initialized"}
        
        return await self._model_manager.get_resource_usage()
    
    async def cleanup(self) -> None:
        """Clean up all resources and shut down services."""
        try:
            if self._model_manager:
                await self._model_manager.cleanup()
                self._model_manager = None
            
            self._initialized = False
            logger.info("LLM Service Container cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during LLM Service Container cleanup: {str(e)}")


def create_model_manager() -> Optional[ModelManager]:
    """
    Factory function to create a ModelManager instance.
    
    Returns:
        ModelManager instance or None if not available
    """
    if ModelManager is None:
        logger.warning("ModelManager not available - check LLM service dependencies")
        return None
    
    return ModelManager()


async def get_service_health() -> Dict[str, Any]:
    """
    Convenience function to check health of all LLM services.
    
    Returns:
        Health status dictionary
    """
    try:
        manager = create_model_manager()
        if manager:
            return await manager.check_all_services_health()
        else:
            return {
                "phi3": False,
                "gemma": False,
                "mistral": False,
                "all_healthy": False,
                "error": "LLM services not available"
            }
    except Exception as e:
        return {
            "phi3": False,
            "gemma": False,
            "mistral": False,
            "all_healthy": False,
            "error": str(e)
        }


def check_llm_availability() -> Dict[str, bool]:
    """
    Check which LLM services are available for import.
    
    Returns:
        Dictionary indicating availability of each service
    """
    return {
        "phi3_service": Phi3Service is not None,
        "gemma_service": GemmaService is not None,
        "mistral_service": MistralService is not None,
        "model_manager": ModelManager is not None,
        "all_available": all([
            Phi3Service is not None,
            GemmaService is not None,
            MistralService is not None,
            ModelManager is not None
        ])
    }


# Global service container instance (can be used as singleton)
_global_container = None


async def get_global_container() -> LLMServiceContainer:
    """
    Get or create the global LLM service container.
    
    Returns:
        Global LLMServiceContainer instance
    """
    global _global_container
    
    if _global_container is None:
        _global_container = LLMServiceContainer()
        await _global_container.initialize()
    
    return _global_container


async def cleanup_global_container() -> None:
    """Clean up the global service container."""
    global _global_container
    
    if _global_container:
        await _global_container.cleanup()
        _global_container = None


# Log package initialization
if all([Phi3Service, GemmaService, MistralService, ModelManager]):
    logger.info("LLM services package loaded successfully")
else:
    logger.warning("Some LLM services are not available - check dependencies")