"""
Mistral 7B Instruct service for application automation in the job automation system.

This service handles automated form filling, application submission, and interaction
with job portals using Mistral 7B Instruct model. Provides intelligent form field
detection, data mapping, and automated application workflows.

Features:
- Automated form field detection and mapping
- Intelligent application form filling
- Multi-step application process handling
- Error detection and recovery
- Application status tracking
- Portal-specific optimization
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import httpx
import re
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings
from app.core.exceptions import ServiceError, ModelNotAvailableError, ApplicationError
from app.utils.text_processing import clean_text, extract_keywords
from app.utils.validation import validate_user_data, validate_application_data

logger = logging.getLogger(__name__)


class ApplicationStatus(Enum):
    """Application submission status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"
    REQUIRES_MANUAL = "requires_manual"


@dataclass
class FormField:
    """Represents a form field for application."""
    name: str
    field_type: str
    required: bool
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None
    max_length: Optional[int] = None
    validation_pattern: Optional[str] = None


@dataclass
class ApplicationResult:
    """Result of application submission attempt."""
    status: ApplicationStatus
    job_id: str
    portal_url: str
    submission_id: Optional[str]
    filled_fields: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    next_steps: List[str]
    completion_percentage: float
    submitted_at: Optional[datetime]


class MistralService:
    """Service for application automation using Mistral 7B Instruct model."""
    
    def __init__(self):
        self.service_url = settings.MISTRAL_SERVICE_URL
        self.model_name = "mistral-7b-instruct"
        self.max_tokens = 8192
        self.temperature = 0.2  # Low temperature for precise instructions
        self.is_initialized = False
        self.client = None
        
    async def initialize(self) -> bool:
        """
        Initialize the Mistral service and check model availability.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.client = httpx.AsyncClient(timeout=60.0)
            
            # Check if model server is available
            health_status = await self.health_check()
            if health_status:
                self.is_initialized = True
                logger.info("Mistral 7B Instruct service initialized successfully")
                return True
            else:
                raise ServiceError("Mistral service health check failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize Mistral service: {str(e)}")
            self.is_initialized = False
            return False
    
    async def health_check(self) -> bool:
        """
        Check if the Mistral service is healthy and responding.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self.client:
                return False
                
            response = await self.client.get(f"{self.service_url}/health")
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Mistral health check failed: {str(e)}")
            return False
    
    async def analyze_application_form(
        self,
        form_html: str,
        portal_type: str = "general",
        job_url: Optional[str] = None
    ) -> List[FormField]:
        """
        Analyze application form structure and identify fields.
        
        Args:
            form_html: HTML content of the application form
            portal_type: Type of job portal (linkedin, indeed, custom)
            job_url: URL of the job posting
            
        Returns:
            List of identified form fields with metadata
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Clean HTML content
            cleaned_html = clean_text(form_html)
            
            # Build form analysis prompt
            prompt = await self._build_form_analysis_prompt(
                cleaned_html, portal_type, job_url
            )
            
            # Analyze form structure
            response = await self._call_model(prompt, max_tokens=4096)
            
            # Parse form fields
            form_fields = await self._parse_form_fields_response(response)
            
            logger.info(f"Identified {len(form_fields)} form fields for {portal_type}")
            return form_fields
            
        except Exception as e:
            logger.error(f"Form analysis failed: {str(e)}")
            raise ServiceError(f"Failed to analyze application form: {str(e)}")
    
    async def generate_field_mappings(
        self,
        form_fields: List[FormField],
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate mappings between form fields and user data.
        
        Args:
            form_fields: List of form fields to fill
            user_profile: User's profile information
            job_data: Job posting information
            
        Returns:
            Dictionary mapping field names to values
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Validate inputs
            validate_user_data(user_profile)
            
            # Build mapping prompt
            prompt = await self._build_mapping_prompt(
                form_fields, user_profile, job_data
            )
            
            # Generate mappings
            response = await self._call_model(prompt, max_tokens=3072)
            
            # Parse field mappings
            mappings = await self._parse_field_mappings_response(response)
            
            logger.info(f"Generated mappings for {len(mappings)} fields")
            return mappings
            
        except Exception as e:
            logger.error(f"Field mapping generation failed: {str(e)}")
            raise ServiceError(f"Failed to generate field mappings: {str(e)}")
    
    async def fill_application_form(
        self,
        form_fields: List[FormField],
        field_mappings: Dict[str, Any],
        portal_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Generate form filling instructions and data.
        
        Args:
            form_fields: List of form fields to fill
            field_mappings: Mapping of field names to values
            portal_type: Type of job portal
            
        Returns:
            Form filling instructions and data
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Build form filling prompt
            prompt = await self._build_form_filling_prompt(
                form_fields, field_mappings, portal_type
            )
            
            # Generate filling instructions
            response = await self._call_model(prompt, max_tokens=2048)
            
            # Parse filling instructions
            filling_data = await self._parse_form_filling_response(response)
            
            return {
                "filling_instructions": filling_data,
                "field_count": len(form_fields),
                "mapped_count": len(field_mappings),
                "portal_type": portal_type,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Form filling failed: {str(e)}")
            raise ServiceError(f"Failed to fill application form: {str(e)}")
    
    async def handle_application_workflow(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        portal_config: Dict[str, Any],
        documents: Optional[Dict[str, str]] = None
    ) -> ApplicationResult:
        """
        Handle complete application workflow from analysis to submission.
        
        Args:
            user_profile: User's profile information
            job_data: Job posting data
            portal_config: Portal-specific configuration
            documents: Generated documents (resume, cover letter)
            
        Returns:
            Complete application result
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Build workflow prompt
            prompt = await self._build_workflow_prompt(
                user_profile, job_data, portal_config, documents
            )
            
            # Execute workflow
            response = await self._call_model(prompt, max_tokens=4096)
            
            # Parse workflow result
            workflow_result = await self._parse_workflow_response(response, job_data.get("id"))
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"Application workflow failed: {str(e)}")
            raise ApplicationError(f"Failed to handle application workflow: {str(e)}")
    
    async def validate_application_data(
        self,
        filled_data: Dict[str, Any],
        form_fields: List[FormField]
    ) -> Dict[str, Any]:
        """
        Validate filled application data against form requirements.
        
        Args:
            filled_data: Data to be submitted
            form_fields: Form field requirements
            
        Returns:
            Validation result with errors and warnings
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Build validation prompt
            prompt = await self._build_validation_prompt(filled_data, form_fields)
            
            # Validate data
            response = await self._call_model(prompt, max_tokens=1536)
            
            # Parse validation result
            validation_result = await self._parse_validation_response(response)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Application validation failed: {str(e)}")
            raise ServiceError(f"Failed to validate application data: {str(e)}")
    
    async def generate_followup_strategy(
        self,
        application_result: ApplicationResult,
        job_data: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate follow-up strategy after application submission.
        
        Args:
            application_result: Result of application submission
            job_data: Job posting information
            user_preferences: User's follow-up preferences
            
        Returns:
            Follow-up strategy and timeline
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Build follow-up prompt
            prompt = await self._build_followup_prompt(
                application_result, job_data, user_preferences
            )
            
            # Generate strategy
            response = await self._call_model(prompt, max_tokens=1024)
            
            # Parse follow-up strategy
            strategy = await self._parse_followup_response(response)
            
            return strategy
            
        except Exception as e:
            logger.error(f"Follow-up strategy generation failed: {str(e)}")
            raise ServiceError(f"Failed to generate follow-up strategy: {str(e)}")
    
    async def _call_model(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = None
    ) -> Dict[str, Any]:
        """
        Make API call to Mistral model service.
        
        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Model response dictionary
        """
        if not self.client:
            raise ServiceError("Mistral client not initialized")
            
        try:
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature or self.temperature,
                "model": self.model_name,
                "stream": False
            }
            
            response = await self.client.post(
                f"{self.service_url}/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise ServiceError(f"Model API error: {response.status_code}")
                
        except httpx.RequestError as e:
            logger.error(f"Request to Mistral service failed: {str(e)}")
            raise ServiceError("Mistral service unavailable")
    
    async def _build_form_analysis_prompt(
        self,
        form_html: str,
        portal_type: str,
        job_url: Optional[str]
    ) -> str:
        """Build prompt for form analysis."""
        prompt = f"""
Analyze this job application form and identify all input fields.

FORM HTML:
{form_html[:8000]}  # Truncate if too long

PORTAL TYPE: {portal_type}
{f"JOB URL: {job_url}" if job_url else ""}

Extract all form fields and return in JSON format:
{{
  "form_fields": [
    {{
      "name": "field_name",
      "field_type": "text/email/textarea/select/checkbox/radio/file",
      "required": true/false,
      "label": "Field label",
      "placeholder": "Placeholder text",
      "options": ["option1", "option2"],  # For select/radio fields
      "max_length": 100,  # Character limit
      "validation_pattern": "regex pattern",
      "description": "Field purpose"
    }}
  ],
  "form_structure": {{
    "sections": ["section1", "section2"],
    "multi_step": true/false,
    "file_uploads": ["resume", "cover_letter"],
    "required_documents": ["document1", "document2"]
  }},
  "portal_specific": {{
    "authentication_required": true/false,
    "captcha_present": true/false,
    "terms_acceptance": true/false,
    "special_requirements": ["requirement1", "requirement2"]
  }}
}}

Focus on identifying:
1. All input fields with their types and requirements
2. File upload capabilities
3. Multi-step form structure
4. Required vs optional fields
5. Validation requirements
"""
        return prompt.strip()
    
    async def _build_mapping_prompt(
        self,
        form_fields: List[FormField],
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> str:
        """Build prompt for field mapping."""
        fields_json = [
            {
                "name": field.name,
                "type": field.field_type,
                "required": field.required,
                "options": field.options
            }
            for field in form_fields
        ]
        
        prompt = f"""
Map user profile data to application form fields.

FORM FIELDS:
{json.dumps(fields_json, indent=2)}

USER PROFILE:
{json.dumps(user_profile, indent=2)}

JOB DATA:
{json.dumps(job_data, indent=2)}

Generate field mappings in JSON format:
{{
  "field_mappings": {{
    "field_name_1": "mapped_value_1",
    "field_name_2": "mapped_value_2"
  }},
  "missing_data": ["field1", "field2"],
  "confidence_scores": {{
    "field_name_1": 0.95,
    "field_name_2": 0.80
  }},
  "recommendations": [
    "Consider updating profile with X information",
    "Field Y may need manual review"
  ]
}}

Guidelines:
1. Use exact field names from form
2. Format data appropriately for field types
3. Handle required fields with highest priority
4. Provide alternatives for missing data
5. Consider field validation requirements
"""
        return prompt.strip()
    
    async def _build_form_filling_prompt(
        self,
        form_fields: List[FormField],
        field_mappings: Dict[str, Any],
        portal_type: str
    ) -> str:
        """Build prompt for form filling instructions."""
        prompt = f"""
Generate form filling instructions for application submission.

FORM FIELDS: {len(form_fields)} fields
FIELD MAPPINGS:
{json.dumps(field_mappings, indent=2)}

PORTAL TYPE: {portal_type}

Generate filling instructions in JSON format:
{{
  "filling_sequence": [
    {{
      "field_name": "first_name",
      "value": "John",
      "action": "type",
      "selector": "#first-name",
      "validation": "check if required field is filled"
    }}
  ],
  "file_uploads": [
    {{
      "field_name": "resume_upload",
      "file_type": "pdf",
      "action": "upload",
      "selector": "input[type='file'][name='resume']"
    }}
  ],
  "special_actions": [
    {{
      "action": "accept_terms",
      "selector": "#terms-checkbox",
      "timing": "before_submit"
    }}
  ],
  "validation_checks": [
    "Verify all required fields are filled",
    "Check file uploads are complete",
    "Confirm form validation passes"
  ],
  "error_handling": [
    "If field X fails, try alternative Y",
    "If upload fails, retry with smaller file"
  ]
}}

Focus on:
1. Optimal filling sequence
2. Error prevention strategies
3. Portal-specific quirks
4. Validation requirements
"""
        return prompt.strip()
    
    async def _parse_form_fields_response(self, response: Dict[str, Any]) -> List[FormField]:
        """Parse form fields from model response."""
        content = response.get("content", "")
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                form_fields = []
                
                for field_data in data.get("form_fields", []):
                    form_field = FormField(
                        name=field_data.get("name", ""),
                        field_type=field_data.get("field_type", "text"),
                        required=field_data.get("required", False),
                        options=field_data.get("options"),
                        placeholder=field_data.get("placeholder"),
                        max_length=field_data.get("max_length"),
                        validation_pattern=field_data.get("validation_pattern")
                    )
                    form_fields.append(form_field)
                
                return form_fields
            else:
                logger.warning("No JSON found in form fields response")
                return []
                
        except json.JSONDecodeError:
            logger.error("Failed to parse form fields JSON")
            return []
    
    async def _parse_field_mappings_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse field mappings from model response."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("field_mappings", {})
            else:
                return {}
        except json.JSONDecodeError:
            logger.error("Failed to parse field mappings JSON")
            return {}
    
    async def _parse_form_filling_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse form filling instructions from model response."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"filling_sequence": [], "error": "Failed to parse instructions"}
        except json.JSONDecodeError:
            return {"filling_sequence": [], "error": "JSON parsing failed"}
    
    async def _parse_workflow_response(
        self,
        response: Dict[str, Any],
        job_id: Optional[str]
    ) -> ApplicationResult:
        """Parse workflow response into ApplicationResult."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return ApplicationResult(
                    status=ApplicationStatus(data.get("status", "pending")),
                    job_id=job_id or "unknown",
                    portal_url=data.get("portal_url", ""),
                    submission_id=data.get("submission_id"),
                    filled_fields=data.get("filled_fields", {}),
                    errors=data.get("errors", []),
                    warnings=data.get("warnings", []),
                    next_steps=data.get("next_steps", []),
                    completion_percentage=data.get("completion_percentage", 0.0),
                    submitted_at=datetime.utcnow() if data.get("status") == "submitted" else None
                )
            else:
                return ApplicationResult(
                    status=ApplicationStatus.FAILED,
                    job_id=job_id or "unknown",
                    portal_url="",
                    submission_id=None,
                    filled_fields={},
                    errors=["Failed to parse workflow response"],
                    warnings=[],
                    next_steps=["Manual review required"],
                    completion_percentage=0.0,
                    submitted_at=None
                )
        except (json.JSONDecodeError, ValueError):
            return ApplicationResult(
                status=ApplicationStatus.FAILED,
                job_id=job_id or "unknown",
                portal_url="",
                submission_id=None,
                filled_fields={},
                errors=["JSON parsing failed"],
                warnings=[],
                next_steps=["Manual review required"],
                completion_percentage=0.0,
                submitted_at=None
            )
    
    async def _build_workflow_prompt(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        portal_config: Dict[str, Any],
        documents: Optional[Dict[str, str]]
    ) -> str:
        """Build workflow execution prompt."""
        return f"""
Execute complete application workflow for this job.

USER PROFILE: {json.dumps(user_profile, indent=2)}
JOB DATA: {json.dumps(job_data, indent=2)}
PORTAL CONFIG: {json.dumps(portal_config, indent=2)}
DOCUMENTS: {json.dumps(documents, indent=2) if documents else "None"}

Plan and execute application workflow in JSON:
{{
  "workflow_steps": [
    "Navigate to application page",
    "Fill personal information",
    "Upload documents",
    "Submit application"
  ],
  "estimated_completion": "95%",
  "status": "submitted/pending/failed",
  "filled_fields": {{}},
  "errors": [],
  "warnings": [],
  "next_steps": []
}}
"""
    
    async def _build_validation_prompt(
        self,
        filled_data: Dict[str, Any],
        form_fields: List[FormField]
    ) -> str:
        """Build validation prompt."""
        return f"""
Validate application data against form requirements.

FILLED DATA: {json.dumps(filled_data, indent=2)}
FORM FIELDS: {len(form_fields)} fields

Return validation result in JSON:
{{
  "is_valid": true/false,
  "errors": ["error1", "error2"],
  "warnings": ["warning1", "warning2"],
  "missing_required": ["field1", "field2"],
  "validation_score": 0.95
}}
"""
    
    async def _build_followup_prompt(
        self,
        application_result: ApplicationResult,
        job_data: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]]
    ) -> str:
        """Build follow-up strategy prompt."""
        return f"""
Generate follow-up strategy for job application.

APPLICATION STATUS: {application_result.status.value}
JOB DATA: {json.dumps(job_data, indent=2)}
USER PREFERENCES: {json.dumps(user_preferences, indent=2) if user_preferences else "None"}

Generate strategy in JSON:
{{
  "followup_timeline": [
    {{
      "action": "Send thank you email",
      "timing": "within 24 hours",
      "priority": "high"
    }}
  ],
  "recommended_actions": ["action1", "action2"],
  "contact_information": {{}},
  "next_check_date": "YYYY-MM-DD"
}}
"""
    
    async def _parse_validation_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse validation response."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"is_valid": False, "errors": ["Validation failed"]}
        except json.JSONDecodeError:
            return {"is_valid": False, "errors": ["Validation parsing failed"]}
    
    async def _parse_followup_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse follow-up strategy response."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"followup_timeline": [], "recommended_actions": []}
        except json.JSONDecodeError:
            return {"followup_timeline": [], "recommended_actions": []}
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.is_initialized = False
        logger.info("Mistral service cleaned up successfully")