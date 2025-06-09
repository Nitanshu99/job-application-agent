"""
Model Manager for LLM service lifecycle management in the job automation system.

This manager coordinates between Phi-3, Gemma, and Mistral services, handles
sequential model usage to optimize resource consumption on MacBook Air M4,
and provides unified interface for all LLM operations.

Features:
- Sequential model loading/unloading for memory optimization
- Unified interface for all LLM services
- Health monitoring and automatic recovery
- Resource usage tracking and optimization
- Service coordination and workflow management
- Error handling and fallback strategies
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import psutil
import json

from app.core.config import settings
from app.core.exceptions import ServiceError, ModelNotAvailableError
from app.services.llm.phi3_service import Phi3Service
from app.services.llm.gemma_service import GemmaService, JobMatchResult
from app.services.llm.mistral_service import MistralService, ApplicationResult, ApplicationStatus

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model service status."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    UNLOADING = "unloading"


class WorkflowStep(Enum):
    """Job application workflow steps."""
    JOB_ANALYSIS = "job_analysis"
    DOCUMENT_GENERATION = "document_generation"
    APPLICATION_SUBMISSION = "application_submission"
    FOLLOWUP_PLANNING = "followup_planning"


class ModelManager:
    """
    Manages lifecycle and coordination of all LLM services.
    
    This class provides a unified interface for all LLM operations while
    optimizing resource usage through sequential model loading/unloading.
    """
    
    def __init__(self):
        self.phi3_service = None
        self.gemma_service = None
        self.mistral_service = None
        
        self.model_status = {
            "phi3": ModelStatus.UNLOADED,
            "gemma": ModelStatus.UNLOADED,
            "mistral": ModelStatus.UNLOADED
        }
        
        self.last_used = {
            "phi3": None,
            "gemma": None,
            "mistral": None
        }
        
        self.memory_threshold = 6.0  # GB - Leave 2GB for system on 8GB MacBook
        self.auto_unload_timeout = timedelta(minutes=15)  # Unload after 15min idle
        self.concurrent_models_limit = 2  # Max 2 models loaded simultaneously
        
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> bool:
        """
        Initialize the model manager and prepare services.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            async with self._lock:
                # Initialize service instances (but don't load models yet)
                self.phi3_service = Phi3Service()
                self.gemma_service = GemmaService()
                self.mistral_service = MistralService()
                
                self.is_initialized = True
                logger.info("Model Manager initialized successfully")
                
                # Start background tasks
                asyncio.create_task(self._monitor_resources())
                asyncio.create_task(self._auto_unload_models())
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize Model Manager: {str(e)}")
            self.is_initialized = False
            return False
    
    async def check_all_services_health(self) -> Dict[str, Any]:
        """
        Check health status of all LLM services.
        
        Returns:
            Dictionary with health status for each service
        """
        health_status = {
            "phi3": False,
            "gemma": False,
            "mistral": False,
            "all_healthy": False,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        try:
            # Check each service health
            if self.phi3_service:
                health_status["phi3"] = await self.phi3_service.health_check()
            
            if self.gemma_service:
                health_status["gemma"] = await self.gemma_service.health_check()
            
            if self.mistral_service:
                health_status["mistral"] = await self.mistral_service.health_check()
            
            # Check if all services are healthy
            health_status["all_healthy"] = all([
                health_status["phi3"],
                health_status["gemma"],
                health_status["mistral"]
            ])
            
            logger.info(f"Health check completed: {health_status}")
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status["error"] = str(e)
            return health_status
    
    async def get_available_models(self) -> List[str]:
        """
        Get list of currently available (loaded) models.
        
        Returns:
            List of available model names
        """
        available = []
        
        if (self.model_status["phi3"] == ModelStatus.READY and 
            self.phi3_service and await self.phi3_service.health_check()):
            available.append("phi3-mini")
        
        if (self.model_status["gemma"] == ModelStatus.READY and
            self.gemma_service and await self.gemma_service.health_check()):
            available.append("gemma-7b")
        
        if (self.model_status["mistral"] == ModelStatus.READY and
            self.mistral_service and await self.mistral_service.health_check()):
            available.append("mistral-7b")
        
        return available
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current system resource usage.
        
        Returns:
            Dictionary with memory, CPU, and model usage statistics
        """
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent
                },
                "cpu": {
                    "percent_used": cpu_percent,
                    "core_count": psutil.cpu_count()
                },
                "models": {
                    "loaded_count": sum(1 for status in self.model_status.values() 
                                      if status == ModelStatus.READY),
                    "status": {name: status.value for name, status in self.model_status.items()}
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {str(e)}")
            return {"error": str(e)}
    
    async def execute_complete_workflow(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        workflow_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete job application workflow using all LLM services sequentially.
        
        Args:
            user_profile: User's professional profile
            job_data: Job posting information
            workflow_config: Optional configuration for workflow
            
        Returns:
            Complete workflow results including all steps
        """
        if not self.is_initialized:
            await self.initialize()
        
        workflow_result = {
            "workflow_id": f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "started_at": datetime.utcnow().isoformat(),
            "user_id": user_profile.get("id"),
            "job_id": job_data.get("id"),
            "steps": {},
            "status": "in_progress",
            "errors": [],
            "warnings": []
        }
        
        try:
            # Step 1: Job Analysis (Gemma 7B)
            logger.info("Starting Step 1: Job Analysis with Gemma 7B")
            workflow_result["steps"]["job_analysis"] = await self._execute_job_analysis(
                user_profile, job_data
            )
            
            # Step 2: Document Generation (Phi-3 Mini)
            logger.info("Starting Step 2: Document Generation with Phi-3 Mini")
            workflow_result["steps"]["document_generation"] = await self._execute_document_generation(
                user_profile, job_data, workflow_result["steps"]["job_analysis"]
            )
            
            # Step 3: Application Submission (Mistral 7B)
            logger.info("Starting Step 3: Application Submission with Mistral 7B")
            workflow_result["steps"]["application_submission"] = await self._execute_application_submission(
                user_profile, job_data, workflow_result["steps"]["document_generation"]
            )
            
            # Step 4: Follow-up Planning (Mistral 7B)
            logger.info("Starting Step 4: Follow-up Planning")
            workflow_result["steps"]["followup_planning"] = await self._execute_followup_planning(
                workflow_result["steps"]["application_submission"], job_data
            )
            
            workflow_result["status"] = "completed"
            workflow_result["completed_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Workflow {workflow_result['workflow_id']} completed successfully")
            return workflow_result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            workflow_result["status"] = "failed"
            workflow_result["error"] = str(e)
            workflow_result["failed_at"] = datetime.utcnow().isoformat()
            return workflow_result
    
    async def _execute_job_analysis(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute job analysis step using Gemma 7B."""
        try:
            # Ensure Gemma is loaded
            await self._ensure_model_loaded("gemma")
            
            # Parse job posting if raw text provided
            if "raw_text" in job_data and not job_data.get("parsed_data"):
                parsed_job = await self.gemma_service.parse_job_posting(
                    job_data["raw_text"],
                    job_data.get("url"),
                    job_data.get("company_info")
                )
                job_data.update(parsed_job["parsed_data"])
            
            # Calculate job match
            match_result = await self.gemma_service.calculate_job_match(
                user_profile, job_data
            )
            
            # Analyze skills gap
            skills_gap = await self.gemma_service.analyze_skills_gap(
                user_profile.get("skills", []),
                job_data.get("required_skills", []),
                job_data.get("experience_level", "mid")
            )
            
            # Update last used timestamp
            self.last_used["gemma"] = datetime.utcnow()
            
            return {
                "status": "completed",
                "match_result": match_result.__dict__,
                "skills_gap": skills_gap,
                "parsed_job_data": job_data,
                "model_used": "gemma-7b",
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Job analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "model_used": "gemma-7b"
            }
    
    async def _execute_document_generation(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute document generation step using Phi-3 Mini."""
        try:
            # Unload Gemma and load Phi-3
            await self._ensure_model_loaded("phi3")
            await self._unload_model("gemma")
            
            # Generate resume
            resume_result = await self.phi3_service.generate_resume(
                user_profile, job_data, template="modern"
            )
            
            # Generate cover letter
            cover_letter_result = await self.phi3_service.generate_cover_letter(
                user_profile, job_data, tone="professional"
            )
            
            # Optimize documents if skills gap identified
            optimized_resume = None
            if analysis_result.get("skills_gap", {}).get("missing_critical"):
                job_keywords = job_data.get("required_skills", [])
                optimized_resume = await self.phi3_service.optimize_content(
                    resume_result["content"], job_keywords, "ats"
                )
            
            # Update last used timestamp
            self.last_used["phi3"] = datetime.utcnow()
            
            return {
                "status": "completed",
                "resume": resume_result,
                "cover_letter": cover_letter_result,
                "optimized_resume": optimized_resume,
                "model_used": "phi3-mini",
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document generation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "model_used": "phi3-mini"
            }
    
    async def _execute_application_submission(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        documents: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute application submission step using Mistral 7B."""
        try:
            # Unload Phi-3 and load Mistral
            await self._ensure_model_loaded("mistral")
            await self._unload_model("phi3")
            
            # Handle application workflow
            portal_config = job_data.get("portal_config", {})
            document_content = {
                "resume": documents.get("resume", {}).get("content", ""),
                "cover_letter": documents.get("cover_letter", {}).get("content", "")
            }
            
            application_result = await self.mistral_service.handle_application_workflow(
                user_profile, job_data, portal_config, document_content
            )
            
            # Update last used timestamp
            self.last_used["mistral"] = datetime.utcnow()
            
            return {
                "status": "completed",
                "application_result": application_result.__dict__,
                "model_used": "mistral-7b",
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Application submission failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "model_used": "mistral-7b"
            }
    
    async def _execute_followup_planning(
        self,
        application_result: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute follow-up planning using Mistral 7B."""
        try:
            # Mistral should still be loaded from previous step
            if self.model_status["mistral"] != ModelStatus.READY:
                await self._ensure_model_loaded("mistral")
            
            # Create ApplicationResult object from dict
            app_result_obj = ApplicationResult(
                status=ApplicationStatus(application_result.get("status", "pending")),
                job_id=job_data.get("id", ""),
                portal_url=job_data.get("url", ""),
                submission_id=application_result.get("submission_id"),
                filled_fields=application_result.get("filled_fields", {}),
                errors=application_result.get("errors", []),
                warnings=application_result.get("warnings", []),
                next_steps=application_result.get("next_steps", []),
                completion_percentage=application_result.get("completion_percentage", 0.0),
                submitted_at=application_result.get("submitted_at")
            )
            
            # Generate follow-up strategy
            followup_strategy = await self.mistral_service.generate_followup_strategy(
                app_result_obj, job_data
            )
            
            return {
                "status": "completed",
                "followup_strategy": followup_strategy,
                "model_used": "mistral-7b",
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Follow-up planning failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "model_used": "mistral-7b"
            }
    
    async def _ensure_model_loaded(self, model_name: str) -> bool:
        """
        Ensure a specific model is loaded and ready.
        
        Args:
            model_name: Name of the model (phi3, gemma, mistral)
            
        Returns:
            True if model is ready, False otherwise
        """
        async with self._lock:
            # Check if model is already ready
            if self.model_status[model_name] == ModelStatus.READY:
                service = getattr(self, f"{model_name}_service")
                if service and await service.health_check():
                    return True
            
            # Check memory usage before loading
            if not await self._check_memory_availability():
                await self._free_memory_for_model(model_name)
            
            # Load the model
            try:
                self.model_status[model_name] = ModelStatus.LOADING
                service = getattr(self, f"{model_name}_service")
                
                if service and await service.initialize():
                    self.model_status[model_name] = ModelStatus.READY
                    self.last_used[model_name] = datetime.utcnow()
                    logger.info(f"Model {model_name} loaded successfully")
                    return True
                else:
                    self.model_status[model_name] = ModelStatus.ERROR
                    logger.error(f"Failed to load model {model_name}")
                    return False
                    
            except Exception as e:
                self.model_status[model_name] = ModelStatus.ERROR
                logger.error(f"Error loading model {model_name}: {str(e)}")
                return False
    
    async def _unload_model(self, model_name: str) -> bool:
        """
        Unload a specific model to free memory.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            if self.model_status[model_name] in [ModelStatus.READY, ModelStatus.BUSY]:
                self.model_status[model_name] = ModelStatus.UNLOADING
                
                service = getattr(self, f"{model_name}_service")
                if service and hasattr(service, 'cleanup'):
                    await service.cleanup()
                
                self.model_status[model_name] = ModelStatus.UNLOADED
                self.last_used[model_name] = None
                logger.info(f"Model {model_name} unloaded successfully")
                return True
            return True
            
        except Exception as e:
            logger.error(f"Error unloading model {model_name}: {str(e)}")
            self.model_status[model_name] = ModelStatus.ERROR
            return False
    
    async def _check_memory_availability(self) -> bool:
        """Check if there's enough memory available for loading a model."""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            return available_gb >= (8.0 - self.memory_threshold)  # Need at least 2GB free
        except:
            return False
    
    async def _free_memory_for_model(self, target_model: str) -> None:
        """Free memory by unloading other models."""
        loaded_models = [
            name for name, status in self.model_status.items() 
            if status == ModelStatus.READY and name != target_model
        ]
        
        # Sort by last used time (oldest first)
        loaded_models.sort(
            key=lambda x: self.last_used.get(x, datetime.min),
            reverse=False
        )
        
        # Unload models until we have enough memory
        for model_name in loaded_models:
            await self._unload_model(model_name)
            if await self._check_memory_availability():
                break
    
    async def _monitor_resources(self) -> None:
        """Background task to monitor system resources."""
        while self.is_initialized:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                memory = psutil.virtual_memory()
                memory_usage_gb = memory.used / (1024**3)
                
                # If memory usage is too high, unload idle models
                if memory_usage_gb > self.memory_threshold:
                    logger.warning(f"High memory usage: {memory_usage_gb:.2f}GB")
                    await self._unload_idle_models()
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {str(e)}")
    
    async def _auto_unload_models(self) -> None:
        """Background task to automatically unload idle models."""
        while self.is_initialized:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = datetime.utcnow()
                
                for model_name, last_used_time in self.last_used.items():
                    if (last_used_time and 
                        self.model_status[model_name] == ModelStatus.READY and
                        current_time - last_used_time > self.auto_unload_timeout):
                        
                        logger.info(f"Auto-unloading idle model: {model_name}")
                        await self._unload_model(model_name)
                
            except Exception as e:
                logger.error(f"Auto-unload error: {str(e)}")
    
    async def _unload_idle_models(self) -> None:
        """Unload models that haven't been used recently."""
        current_time = datetime.utcnow()
        
        for model_name, last_used_time in self.last_used.items():
            if (last_used_time and 
                self.model_status[model_name] == ModelStatus.READY and
                current_time - last_used_time > timedelta(minutes=5)):
                
                await self._unload_model(model_name)
    
    async def cleanup(self) -> None:
        """Clean up all resources and shut down services."""
        try:
            self.is_initialized = False
            
            # Unload all models
            for model_name in ["phi3", "gemma", "mistral"]:
                await self._unload_model(model_name)
            
            logger.info("Model Manager cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get status of a specific workflow (placeholder for future implementation).
        
        Args:
            workflow_id: ID of the workflow to check
            
        Returns:
            Workflow status information
        """
        # This would typically query a database or cache
        # For now, return a placeholder response
        return {
            "workflow_id": workflow_id,
            "status": "unknown",
            "message": "Workflow status tracking not implemented yet"
        }
    
    def __str__(self) -> str:
        """String representation of ModelManager state."""
        status_summary = {name: status.value for name, status in self.model_status.items()}
        return f"ModelManager(initialized={self.is_initialized}, status={status_summary})"