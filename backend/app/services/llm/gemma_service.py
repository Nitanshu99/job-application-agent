"""
Gemma 7B service for job matching and analysis in the job automation system.

This service handles intelligent job parsing, relevance scoring, and matching
using Google's Gemma 7B model. Optimized for analytical tasks and provides
detailed insights into job requirements and user compatibility.

Features:
- Job posting parsing and analysis
- Intelligent job-user matching with relevance scoring
- Skills gap analysis and recommendations
- Company culture assessment
- Salary and benefits analysis
- Market trend insights
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import httpx
import re
from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import ServiceError, ModelNotAvailableError
from app.utils.text_processing import clean_text, extract_keywords, similarity_score
from app.utils.validation import validate_job_data, validate_user_data

logger = logging.getLogger(__name__)


@dataclass
class JobMatchResult:
    """Result of job matching analysis."""
    job_id: str
    relevance_score: float
    skills_match: float
    experience_match: float
    cultural_fit: float
    salary_fit: float
    missing_skills: List[str]
    matching_skills: List[str]
    recommendations: List[str]
    confidence: float


class GemmaService:
    """Service for job analysis and matching using Gemma 7B model."""
    
    def __init__(self):
        self.service_url = settings.GEMMA_SERVICE_URL
        self.model_name = "gemma-7b"
        self.max_tokens = 8192
        self.temperature = 0.3  # Lower temperature for analytical tasks
        self.is_initialized = False
        self.client = None
        
    async def initialize(self) -> bool:
        """
        Initialize the Gemma service and check model availability.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.client = httpx.AsyncClient(timeout=45.0)
            
            # Check if model server is available
            health_status = await self.health_check()
            if health_status:
                self.is_initialized = True
                logger.info("Gemma 7B service initialized successfully")
                return True
            else:
                raise ServiceError("Gemma service health check failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize Gemma service: {str(e)}")
            self.is_initialized = False
            return False
    
    async def health_check(self) -> bool:
        """
        Check if the Gemma service is healthy and responding.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self.client:
                return False
                
            response = await self.client.get(f"{self.service_url}/health")
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Gemma health check failed: {str(e)}")
            return False
    
    async def parse_job_posting(
        self,
        job_text: str,
        job_url: Optional[str] = None,
        company_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse and extract structured data from a job posting.
        
        Args:
            job_text: Raw job posting text
            job_url: URL of the job posting
            company_info: Additional company information
            
        Returns:
            Structured job data including requirements, skills, etc.
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Clean and prepare job text
            cleaned_text = clean_text(job_text)
            
            # Build parsing prompt
            prompt = await self._build_job_parsing_prompt(
                cleaned_text, job_url, company_info
            )
            
            # Analyze job posting
            response = await self._call_model(prompt, max_tokens=4096)
            
            # Parse structured response
            job_data = await self._parse_job_analysis_response(response)
            
            return {
                "parsed_data": job_data,
                "raw_text": job_text,
                "url": job_url,
                "analyzed_at": datetime.utcnow().isoformat(),
                "model": self.model_name,
                "confidence": job_data.get("parsing_confidence", 0.0)
            }
            
        except Exception as e:
            logger.error(f"Job parsing failed: {str(e)}")
            raise ServiceError(f"Failed to parse job posting: {str(e)}")
    
    async def calculate_job_match(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None
    ) -> JobMatchResult:
        """
        Calculate comprehensive job match score and analysis.
        
        Args:
            user_profile: User's professional profile
            job_data: Parsed job posting data
            preferences: User's job preferences
            
        Returns:
            Detailed job match analysis
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            # Validate inputs
            validate_user_data(user_profile)
            validate_job_data(job_data)
            
            # Build matching analysis prompt
            prompt = await self._build_matching_prompt(
                user_profile, job_data, preferences
            )
            
            # Perform matching analysis
            response = await self._call_model(prompt, max_tokens=3072)
            
            # Parse matching results
            match_result = await self._parse_matching_response(response, job_data.get("id"))
            
            return match_result
            
        except Exception as e:
            logger.error(f"Job matching failed: {str(e)}")
            raise ServiceError(f"Failed to calculate job match: {str(e)}")
    
    async def analyze_skills_gap(
        self,
        user_skills: List[str],
        required_skills: List[str],
        job_level: str = "mid"
    ) -> Dict[str, Any]:
        """
        Analyze skills gap and provide learning recommendations.
        
        Args:
            user_skills: List of user's current skills
            required_skills: List of skills required for job
            job_level: Job level (entry, mid, senior, executive)
            
        Returns:
            Skills gap analysis with recommendations
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            prompt = await self._build_skills_gap_prompt(
                user_skills, required_skills, job_level
            )
            
            response = await self._call_model(prompt, max_tokens=2048)
            
            return await self._parse_skills_gap_response(response)
            
        except Exception as e:
            logger.error(f"Skills gap analysis failed: {str(e)}")
            raise ServiceError(f"Failed to analyze skills gap: {str(e)}")
    
    async def assess_company_culture(
        self,
        company_description: str,
        job_description: str,
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess company culture fit based on descriptions and user preferences.
        
        Args:
            company_description: Company culture and values description
            job_description: Job posting description
            user_preferences: User's cultural preferences
            
        Returns:
            Culture fit analysis and recommendations
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            prompt = await self._build_culture_assessment_prompt(
                company_description, job_description, user_preferences
            )
            
            response = await self._call_model(prompt, max_tokens=1536)
            
            return await self._parse_culture_assessment_response(response)
            
        except Exception as e:
            logger.error(f"Culture assessment failed: {str(e)}")
            raise ServiceError(f"Failed to assess company culture: {str(e)}")
    
    async def analyze_market_trends(
        self,
        job_titles: List[str],
        location: str,
        industry: str
    ) -> Dict[str, Any]:
        """
        Analyze job market trends for specific roles and locations.
        
        Args:
            job_titles: List of job titles to analyze
            location: Geographic location
            industry: Industry sector
            
        Returns:
            Market trend analysis and insights
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            prompt = await self._build_market_trends_prompt(
                job_titles, location, industry
            )
            
            response = await self._call_model(prompt, max_tokens=2560)
            
            return await self._parse_market_trends_response(response)
            
        except Exception as e:
            logger.error(f"Market trends analysis failed: {str(e)}")
            raise ServiceError(f"Failed to analyze market trends: {str(e)}")
    
    async def _call_model(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = None
    ) -> Dict[str, Any]:
        """
        Make API call to Gemma model service.
        
        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Model response dictionary
        """
        if not self.client:
            raise ServiceError("Gemma client not initialized")
            
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
            logger.error(f"Request to Gemma service failed: {str(e)}")
            raise ServiceError("Gemma service unavailable")
    
    async def _build_job_parsing_prompt(
        self,
        job_text: str,
        job_url: Optional[str],
        company_info: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for job posting parsing."""
        prompt = f"""
Analyze this job posting and extract structured information.

JOB POSTING TEXT:
{job_text}

{"URL: " + job_url if job_url else ""}
{f"COMPANY INFO: {json.dumps(company_info, indent=2)}" if company_info else ""}

Extract and return the following information in JSON format:
{{
  "title": "Job title",
  "company": "Company name",
  "location": "Job location (city, state/country)",
  "remote_options": "Remote work options (fully remote, hybrid, on-site)",
  "employment_type": "Full-time, part-time, contract, etc.",
  "experience_level": "Entry, mid, senior, executive",
  "salary_range": {{
    "min": number,
    "max": number,
    "currency": "USD",
    "period": "annual/hourly"
  }},
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill1", "skill2", ...],
  "technologies": ["tech1", "tech2", ...],
  "requirements": {{
    "education": "Education requirements",
    "experience_years": number,
    "certifications": ["cert1", "cert2", ...],
    "languages": ["language1", "language2", ...]
  }},
  "responsibilities": ["responsibility1", "responsibility2", ...],
  "benefits": ["benefit1", "benefit2", ...],
  "company_size": "startup/small/medium/large/enterprise",
  "industry": "Industry sector",
  "application_deadline": "YYYY-MM-DD or null",
  "key_qualifications": ["qualification1", "qualification2", ...],
  "growth_opportunities": "Career growth potential",
  "company_culture": "Culture and values description",
  "parsing_confidence": 0.95
}}

Be thorough and accurate. Extract all available information.
"""
        return prompt.strip()
    
    async def _build_matching_prompt(
        self,
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        preferences: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for job matching analysis."""
        prompt = f"""
Analyze the match between this user profile and job posting.

USER PROFILE:
{json.dumps(user_profile, indent=2)}

JOB POSTING:
{json.dumps(job_data, indent=2)}

{f"USER PREFERENCES: {json.dumps(preferences, indent=2)}" if preferences else ""}

Provide comprehensive matching analysis in JSON format:
{{
  "relevance_score": 0.85,
  "skills_match": 0.75,
  "experience_match": 0.90,
  "cultural_fit": 0.70,
  "salary_fit": 0.80,
  "missing_skills": ["skill1", "skill2"],
  "matching_skills": ["skill1", "skill2"],
  "experience_gaps": ["gap1", "gap2"],
  "strengths": ["strength1", "strength2"],
  "recommendations": [
    "Highlight your experience with X in your application",
    "Consider learning Y to strengthen your profile"
  ],
  "confidence": 0.92,
  "overall_recommendation": "strong_match/good_match/weak_match/no_match",
  "application_strategy": "Detailed strategy for applying to this role"
}}

Consider:
- Skills alignment (required vs. user skills)
- Experience level match
- Career progression fit
- Location and remote work preferences
- Salary expectations vs. offer
- Company culture alignment
- Growth opportunities

Provide actionable insights and specific recommendations.
"""
        return prompt.strip()
    
    async def _build_skills_gap_prompt(
        self,
        user_skills: List[str],
        required_skills: List[str],
        job_level: str
    ) -> str:
        """Build prompt for skills gap analysis."""
        prompt = f"""
Analyze the skills gap between user abilities and job requirements.

USER SKILLS:
{json.dumps(user_skills, indent=2)}

REQUIRED SKILLS:
{json.dumps(required_skills, indent=2)}

JOB LEVEL: {job_level}

Provide detailed skills gap analysis in JSON format:
{{
  "gap_analysis": {{
    "missing_critical": ["skill1", "skill2"],
    "missing_preferred": ["skill3", "skill4"],
    "transferable": ["skill5", "skill6"],
    "strengths": ["skill7", "skill8"]
  }},
  "learning_recommendations": [
    {{
      "skill": "skill_name",
      "priority": "high/medium/low",
      "time_to_learn": "weeks/months",
      "resources": ["resource1", "resource2"],
      "certification_options": ["cert1", "cert2"]
    }}
  ],
  "alternative_roles": ["role1", "role2"],
  "readiness_score": 0.75,
  "time_to_ready": "3-6 months",
  "immediate_actions": ["action1", "action2"]
}}

Focus on practical, actionable learning paths.
"""
        return prompt.strip()
    
    async def _parse_job_analysis_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse job analysis response from model."""
        content = response.get("content", "")
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback: basic parsing
                return {"raw_analysis": content, "parsing_confidence": 0.3}
        except json.JSONDecodeError:
            logger.warning("Failed to parse job analysis JSON response")
            return {"raw_analysis": content, "parsing_confidence": 0.1}
    
    async def _parse_matching_response(
        self,
        response: Dict[str, Any],
        job_id: Optional[str]
    ) -> JobMatchResult:
        """Parse job matching response into structured result."""
        content = response.get("content", "")
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return JobMatchResult(
                    job_id=job_id or "unknown",
                    relevance_score=data.get("relevance_score", 0.0),
                    skills_match=data.get("skills_match", 0.0),
                    experience_match=data.get("experience_match", 0.0),
                    cultural_fit=data.get("cultural_fit", 0.0),
                    salary_fit=data.get("salary_fit", 0.0),
                    missing_skills=data.get("missing_skills", []),
                    matching_skills=data.get("matching_skills", []),
                    recommendations=data.get("recommendations", []),
                    confidence=data.get("confidence", 0.0)
                )
            else:
                # Fallback result
                return JobMatchResult(
                    job_id=job_id or "unknown",
                    relevance_score=0.0,
                    skills_match=0.0,
                    experience_match=0.0,
                    cultural_fit=0.0,
                    salary_fit=0.0,
                    missing_skills=[],
                    matching_skills=[],
                    recommendations=["Analysis failed - manual review needed"],
                    confidence=0.0
                )
        except json.JSONDecodeError:
            logger.warning("Failed to parse matching JSON response")
            return JobMatchResult(
                job_id=job_id or "unknown",
                relevance_score=0.0,
                skills_match=0.0,
                experience_match=0.0,
                cultural_fit=0.0,
                salary_fit=0.0,
                missing_skills=[],
                matching_skills=[],
                recommendations=["Parsing failed - manual review needed"],
                confidence=0.0
            )
    
    async def _parse_skills_gap_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse skills gap analysis response."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"raw_analysis": content, "analysis_quality": "low"}
        except json.JSONDecodeError:
            return {"raw_analysis": content, "analysis_quality": "failed"}
    
    async def _parse_culture_assessment_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse culture assessment response."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"assessment": content, "confidence": 0.3}
        except json.JSONDecodeError:
            return {"assessment": content, "confidence": 0.1}
    
    async def _parse_market_trends_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse market trends analysis response."""
        content = response.get("content", "")
        
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"trends_summary": content, "confidence": 0.3}
        except json.JSONDecodeError:
            return {"trends_summary": content, "confidence": 0.1}
    
    async def _build_culture_assessment_prompt(
        self,
        company_description: str,
        job_description: str,
        user_preferences: Dict[str, Any]
    ) -> str:
        """Build prompt for culture assessment."""
        return f"""
Assess company culture fit based on available information.

COMPANY DESCRIPTION:
{company_description}

JOB DESCRIPTION:
{job_description}

USER PREFERENCES:
{json.dumps(user_preferences, indent=2)}

Analyze culture fit and return JSON:
{{
  "culture_fit_score": 0.80,
  "work_life_balance": 0.75,
  "growth_opportunities": 0.85,
  "team_dynamics": 0.70,
  "values_alignment": 0.90,
  "concerns": ["concern1", "concern2"],
  "positives": ["positive1", "positive2"],
  "recommendation": "good_fit/potential_fit/poor_fit"
}}
"""
    
    async def _build_market_trends_prompt(
        self,
        job_titles: List[str],
        location: str,
        industry: str
    ) -> str:
        """Build prompt for market trends analysis."""
        return f"""
Analyze job market trends for these roles.

JOB TITLES: {json.dumps(job_titles)}
LOCATION: {location}
INDUSTRY: {industry}

Provide market analysis in JSON:
{{
  "demand_level": "high/medium/low",
  "salary_trends": "increasing/stable/decreasing",
  "skill_trends": ["emerging_skill1", "emerging_skill2"],
  "growth_outlook": "positive/neutral/negative",
  "competition_level": "high/medium/low",
  "recommendations": ["rec1", "rec2"]
}}
"""
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.is_initialized = False
        logger.info("Gemma service cleaned up successfully")