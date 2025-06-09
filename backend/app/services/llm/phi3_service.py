"""
Phi-3 Mini service for document generation in the job automation system.

This service handles resume and cover letter generation using Microsoft's Phi-3 Mini model.
Optimized for MacBook Air M4 with efficient memory usage and fast inference times.

Features:
- Tailored resume generation based on job requirements
- Personalized cover letter creation
- Multiple document templates and formats
- Efficient memory management for resource-constrained environments
- Async processing with proper error handling
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import ServiceError, ModelNotAvailableError
from app.utils.text_processing import clean_text, extract_keywords
from app.utils.validation import validate_user_data, validate_job_data

logger = logging.getLogger(__name__)


class Phi3Service:
    """Service for document generation using Phi-3 Mini model."""
    
    def __init__(self):
        self.service_url = settings.PHI3_SERVICE_URL
        self.model_name = "phi3-mini"
        self.max_tokens = 4096
        self.temperature = 0.7
        self.is_initialized = False
        self.client = None
        
    async def initialize(self) -> bool:
        """
        Initialize the Phi-3 service and check model availability.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            
            # Check if model server is available
            health_status = await self.health_check()
            if health_status:
                self.is_initialized = True
                logger.info("Phi-3 Mini service initialized successfully")
                return True
            else:
                raise ServiceError("Phi-3 service health check failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize Phi-3 service: {str(e)}")
            self.is_initialized = False
            return False
    
    async def health_check(self) -> bool:
        """
        Check if the Phi-3 service is healthy and responding.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self.client:
                return False
                
            response = await self.client.get(f"{self.service_url}/health")
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Phi-3 health check failed: {str(e)}")
            return False
    
    async def generate_resume(
        self,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        template: str = "modern",
        format_type: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate a tailored resume for a specific job application.
        
        Args:
            user_profile: User's professional profile and experience
            job_details: Job posting details and requirements
            template: Resume template style (modern, classic, creative)
            format_type: Output format (markdown, html, json)
            
        Returns:
            Dictionary containing generated resume content and metadata
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Validate inputs
            validate_user_data(user_profile)
            validate_job_data(job_details)
            
            # Prepare prompt for resume generation
            prompt = await self._build_resume_prompt(user_profile, job_details, template)
            
            # Generate resume content
            response = await self._call_model(prompt, max_tokens=2048)
            
            # Parse and structure the response
            resume_content = await self._parse_resume_response(response, format_type)
            
            return {
                "content": resume_content,
                "template": template,
                "format": format_type,
                "job_id": job_details.get("id"),
                "user_id": user_profile.get("id"),
                "generated_at": datetime.utcnow().isoformat(),
                "model": self.model_name,
                "tokens_used": response.get("usage", {}).get("total_tokens", 0)
            }
            
        except Exception as e:
            logger.error(f"Resume generation failed: {str(e)}")
            raise ServiceError(f"Failed to generate resume: {str(e)}")
    
    async def generate_cover_letter(
        self,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        tone: str = "professional",
        length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a personalized cover letter for a job application.
        
        Args:
            user_profile: User's professional profile and information
            job_details: Job posting details and company information
            tone: Writing tone (professional, casual, enthusiastic)
            length: Length preference (short, medium, long)
            
        Returns:
            Dictionary containing generated cover letter and metadata
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Validate inputs
            validate_user_data(user_profile)
            validate_job_data(job_details)
            
            # Prepare prompt for cover letter generation
            prompt = await self._build_cover_letter_prompt(
                user_profile, job_details, tone, length
            )
            
            # Generate cover letter content
            response = await self._call_model(prompt, max_tokens=1024)
            
            # Parse and format the response
            cover_letter_content = await self._parse_cover_letter_response(response)
            
            return {
                "content": cover_letter_content,
                "tone": tone,
                "length": length,
                "job_id": job_details.get("id"),
                "user_id": user_profile.get("id"),
                "generated_at": datetime.utcnow().isoformat(),
                "model": self.model_name,
                "tokens_used": response.get("usage", {}).get("total_tokens", 0)
            }
            
        except Exception as e:
            logger.error(f"Cover letter generation failed: {str(e)}")
            raise ServiceError(f"Failed to generate cover letter: {str(e)}")
    
    async def optimize_content(
        self,
        content: str,
        job_keywords: List[str],
        optimization_type: str = "ats"
    ) -> Dict[str, Any]:
        """
        Optimize document content for ATS systems and job relevance.
        
        Args:
            content: Document content to optimize
            job_keywords: Important keywords from job posting
            optimization_type: Type of optimization (ats, keywords, readability)
            
        Returns:
            Dictionary containing optimized content and suggestions
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            prompt = await self._build_optimization_prompt(
                content, job_keywords, optimization_type
            )
            
            response = await self._call_model(prompt, max_tokens=1536)
            
            return {
                "optimized_content": response.get("content", ""),
                "suggestions": response.get("suggestions", []),
                "optimization_type": optimization_type,
                "score_improvement": response.get("score_improvement", 0),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Content optimization failed: {str(e)}")
            raise ServiceError(f"Failed to optimize content: {str(e)}")
    
    async def _call_model(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = None
    ) -> Dict[str, Any]:
        """
        Make API call to Phi-3 model service.
        
        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Model response dictionary
        """
        if not self.client:
            raise ServiceError("Phi-3 client not initialized")
            
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
            logger.error(f"Request to Phi-3 service failed: {str(e)}")
            raise ServiceError("Phi-3 service unavailable")
    
    async def _build_resume_prompt(
        self,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        template: str
    ) -> str:
        """Build prompt for resume generation."""
        prompt = f"""
Create a professional resume tailored for this job application.

USER PROFILE:
Name: {user_profile.get('full_name', 'N/A')}
Email: {user_profile.get('email', 'N/A')}
Phone: {user_profile.get('phone', 'N/A')}
Location: {user_profile.get('location', 'N/A')}

EXPERIENCE:
{json.dumps(user_profile.get('experience', []), indent=2)}

SKILLS:
{', '.join(user_profile.get('skills', []))}

EDUCATION:
{json.dumps(user_profile.get('education', []), indent=2)}

JOB DETAILS:
Title: {job_details.get('title', 'N/A')}
Company: {job_details.get('company', 'N/A')}
Requirements: {job_details.get('requirements', 'N/A')}
Description: {job_details.get('description', 'N/A')}

Template Style: {template}

Generate a tailored resume that:
1. Highlights relevant experience for this specific role
2. Emphasizes skills mentioned in the job requirements
3. Uses action verbs and quantifiable achievements
4. Follows {template} formatting style
5. Is optimized for ATS systems

Format as clean, structured text with clear sections.
"""
        return prompt.strip()
    
    async def _build_cover_letter_prompt(
        self,
        user_profile: Dict[str, Any],
        job_details: Dict[str, Any],
        tone: str,
        length: str
    ) -> str:
        """Build prompt for cover letter generation."""
        length_guidance = {
            "short": "Keep it concise, 2-3 paragraphs maximum",
            "medium": "Write 3-4 paragraphs with good detail",
            "long": "Create a comprehensive 4-5 paragraph letter"
        }
        
        prompt = f"""
Write a compelling cover letter for this job application.

USER PROFILE:
Name: {user_profile.get('full_name', 'N/A')}
Current Role: {user_profile.get('current_role', 'N/A')}
Experience Summary: {user_profile.get('summary', 'N/A')}
Key Skills: {', '.join(user_profile.get('skills', [])[:5])}

JOB DETAILS:
Position: {job_details.get('title', 'N/A')}
Company: {job_details.get('company', 'N/A')}
Requirements: {job_details.get('requirements', 'N/A')}
Company Culture: {job_details.get('culture', 'N/A')}

Instructions:
- Tone: {tone}
- Length: {length_guidance.get(length, 'medium length')}
- Address why you're interested in this specific role and company
- Highlight 2-3 most relevant experiences
- Show enthusiasm and cultural fit
- Include a strong closing with call to action
- Use proper business letter format

Write a personalized, engaging cover letter that stands out.
"""
        return prompt.strip()
    
    async def _build_optimization_prompt(
        self,
        content: str,
        job_keywords: List[str],
        optimization_type: str
    ) -> str:
        """Build prompt for content optimization."""
        prompt = f"""
Optimize this document content for better job application success.

ORIGINAL CONTENT:
{content}

JOB KEYWORDS:
{', '.join(job_keywords)}

OPTIMIZATION TYPE: {optimization_type}

Please:
1. Improve keyword density for ATS systems
2. Enhance readability and flow
3. Strengthen action verbs and impact statements
4. Ensure proper formatting and structure
5. Provide specific suggestions for improvement

Return optimized content and a list of improvements made.
"""
        return prompt.strip()
    
    async def _parse_resume_response(
        self,
        response: Dict[str, Any],
        format_type: str
    ) -> str:
        """Parse and format resume response."""
        content = response.get("content", "")
        
        if format_type == "json":
            # Try to structure content as JSON
            try:
                return json.dumps({"resume": content}, indent=2)
            except:
                return content
        elif format_type == "html":
            # Convert to basic HTML structure
            return f"<div class='resume'>{content.replace('\n', '<br>')}</div>"
        else:
            # Return as markdown (default)
            return content
    
    async def _parse_cover_letter_response(self, response: Dict[str, Any]) -> str:
        """Parse cover letter response."""
        return response.get("content", "")
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.is_initialized = False
        logger.info("Phi-3 service cleaned up successfully")