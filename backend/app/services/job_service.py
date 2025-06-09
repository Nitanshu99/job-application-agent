"""
Job service for AI-powered job automation system.

This service handles job matching, parsing, and analysis using the Gemma 7B model.
It provides intelligent job matching based on user profiles, job relevance scoring,
and comprehensive job data processing.

Features:
- Job parsing and analysis using Gemma 7B
- Intelligent job matching with relevance scoring
- Skills gap analysis and recommendations
- Job market trends and insights
- Custom job portal integration
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import re

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobMatch
from app.services.llm.gemma_service import GemmaService
from app.utils.text_processing import clean_text, extract_keywords, similarity_score
from app.utils.validation import validate_job_data

logger = logging.getLogger(__name__)


class JobService:
    """Service for job matching, parsing, and analysis using Gemma 7B."""
    
    def __init__(self):
        self.gemma_service = None
        
    async def get_gemma_service(self) -> GemmaService:
        """Get or initialize Gemma service."""
        if not self.gemma_service:
            self.gemma_service = GemmaService()
            await self.gemma_service.initialize()
        return self.gemma_service
    
    async def parse_job_posting(
        self,
        job_url: str,
        raw_content: str,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse and extract structured data from a job posting using Gemma 7B.
        
        Args:
            job_url: URL of the job posting
            raw_content: Raw HTML/text content of the job posting
            company: Optional company name for context
            
        Returns:
            Dictionary containing parsed job data
        """
        try:
            logger.info(f"Parsing job posting from {job_url}")
            
            # Clean and preprocess the content
            cleaned_content = clean_text(raw_content)
            
            if len(cleaned_content) < 100:
                raise ValueError("Job content too short for meaningful parsing")
            
            # Get Gemma service
            gemma_service = await self.get_gemma_service()
            
            # Parse job posting using Gemma 7B
            parsing_result = await gemma_service.parse_job_posting(
                content=cleaned_content,
                url=job_url,
                company_hint=company
            )
            
            if not parsing_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Job parsing failed: {parsing_result.get('error')}"
                )
            
            parsed_data = parsing_result["parsed_data"]
            
            # Validate and structure the parsed data
            structured_job = await self._structure_job_data(parsed_data, job_url, cleaned_content)
            
            # Extract additional insights
            insights = await self._extract_job_insights(structured_job, cleaned_content)
            structured_job.update(insights)
            
            logger.info(f"Job parsing completed successfully for {structured_job.get('title', 'Unknown')}")
            
            return {
                "success": True,
                "job_data": structured_job,
                "parsing_metadata": {
                    "model_used": "gemma-7b",
                    "parsed_at": datetime.utcnow().isoformat(),
                    "content_length": len(cleaned_content),
                    "confidence_score": parsing_result.get("confidence", 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"Job parsing failed for {job_url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Job parsing failed: {str(e)}")
    
    async def find_matching_jobs(
        self,
        user_id: int,
        job_ids: Optional[List[int]] = None,
        limit: int = 20,
        min_relevance_score: float = 0.6,
        db: Session = None
    ) -> List[JobMatch]:
        """
        Find jobs that match a user's profile with relevance scoring.
        
        Args:
            user_id: ID of the user
            job_ids: Optional list of specific job IDs to analyze
            limit: Maximum number of jobs to return
            min_relevance_score: Minimum relevance score threshold
            db: Database session
            
        Returns:
            List of job matches with relevance scores
        """
        try:
            if not db:
                db = next(get_db())
            
            # Get user profile
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get jobs to analyze
            query = db.query(Job).filter(Job.is_active == True)
            
            if job_ids:
                query = query.filter(Job.id.in_(job_ids))
            
            jobs = query.order_by(desc(Job.posted_date)).limit(limit * 2).all()  # Get more for filtering
            
            if not jobs:
                return []
            
            logger.info(f"Analyzing {len(jobs)} jobs for user {user_id}")
            
            # Get Gemma service for job matching
            gemma_service = await self.get_gemma_service()
            
            job_matches = []
            
            for job in jobs:
                try:
                    # Calculate relevance score using Gemma 7B
                    matching_result = await gemma_service.calculate_job_match(
                        user_profile=await self._prepare_user_profile(user),
                        job_data=await self._prepare_job_data(job)
                    )
                    
                    if matching_result.get("success"):
                        relevance_score = matching_result.get("relevance_score", 0.0)
                        
                        if relevance_score >= min_relevance_score:
                            match_data = JobMatch(
                                job_id=job.id,
                                job=job,
                                relevance_score=relevance_score,
                                matching_skills=matching_result.get("matching_skills", []),
                                skill_gaps=matching_result.get("skill_gaps", []),
                                experience_match=matching_result.get("experience_match", 0.0),
                                location_match=matching_result.get("location_match", 0.0),
                                salary_match=matching_result.get("salary_match", 0.0),
                                reasons=matching_result.get("match_reasons", []),
                                recommendations=matching_result.get("recommendations", [])
                            )
                            job_matches.append(match_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze job {job.id}: {str(e)}")
                    continue
            
            # Sort by relevance score and limit results
            job_matches.sort(key=lambda x: x.relevance_score, reverse=True)
            job_matches = job_matches[:limit]
            
            logger.info(f"Found {len(job_matches)} matching jobs for user {user_id}")
            
            return job_matches
            
        except Exception as e:
            logger.error(f"Job matching failed for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Job matching failed: {str(e)}")
    
    async def analyze_job_market(
        self,
        user_id: int,
        location: Optional[str] = None,
        industry: Optional[str] = None,
        time_range_days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Analyze job market trends and insights for a user.
        
        Args:
            user_id: ID of the user
            location: Optional location filter
            industry: Optional industry filter
            time_range_days: Number of days to analyze
            db: Database session
            
        Returns:
            Dictionary containing market analysis
        """
        try:
            if not db:
                db = next(get_db())
            
            # Get user for context
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Calculate date range
            start_date = datetime.utcnow() - timedelta(days=time_range_days)
            
            # Build query for recent jobs
            query = db.query(Job).filter(
                Job.posted_date >= start_date,
                Job.is_active == True
            )
            
            if location:
                query = query.filter(Job.location.ilike(f"%{location}%"))
            if industry:
                query = query.filter(Job.industry.ilike(f"%{industry}%"))
            
            recent_jobs = query.all()
            
            if not recent_jobs:
                return {"message": "No jobs found for analysis", "job_count": 0}
            
            logger.info(f"Analyzing {len(recent_jobs)} jobs for market trends")
            
            # Get Gemma service
            gemma_service = await self.get_gemma_service()
            
            # Prepare data for analysis
            jobs_data = [await self._prepare_job_data(job) for job in recent_jobs]
            user_profile = await self._prepare_user_profile(user)
            
            # Perform market analysis using Gemma 7B
            analysis_result = await gemma_service.analyze_job_market(
                jobs_data=jobs_data,
                user_profile=user_profile,
                location=location,
                industry=industry
            )
            
            if not analysis_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail="Market analysis failed"
                )
            
            # Process and structure the analysis
            market_analysis = {
                "analysis_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "days_analyzed": time_range_days
                },
                "job_count": len(recent_jobs),
                "trends": analysis_result.get("trends", {}),
                "salary_insights": analysis_result.get("salary_insights", {}),
                "skill_demand": analysis_result.get("skill_demand", {}),
                "company_insights": analysis_result.get("company_insights", {}),
                "recommendations": analysis_result.get("recommendations", []),
                "opportunities": analysis_result.get("opportunities", []),
                "market_competitiveness": analysis_result.get("competitiveness_score", 0.0),
                "user_market_fit": analysis_result.get("user_fit_score", 0.0)
            }
            
            logger.info("Market analysis completed successfully")
            
            return market_analysis
            
        except Exception as e:
            logger.error(f"Market analysis failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Market analysis failed: {str(e)}")
    
    async def create_job(self, job_data: JobCreate, db: Session = None) -> Job:
        """Create a new job record."""
        try:
            if not db:
                db = next(get_db())
            
            # Validate job data
            if not validate_job_data(job_data.dict()):
                raise HTTPException(status_code=400, detail="Invalid job data")
            
            # Create job instance
            job = Job(**job_data.dict())
            job.created_at = datetime.utcnow()
            job.is_active = True
            
            # Extract and store keywords
            if job.description:
                job.keywords = extract_keywords(job.description)
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            logger.info(f"Job created successfully with ID {job.id}")
            return job
            
        except Exception as e:
            logger.error(f"Job creation failed: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Job creation failed: {str(e)}")
    
    async def update_job(self, job_id: int, job_data: JobUpdate, db: Session = None) -> Optional[Job]:
        """Update an existing job record."""
        try:
            if not db:
                db = next(get_db())
            
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            
            # Update job fields
            update_data = job_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(job, field, value)
            
            job.updated_at = datetime.utcnow()
            
            # Update keywords if description changed
            if "description" in update_data and job.description:
                job.keywords = extract_keywords(job.description)
            
            db.commit()
            db.refresh(job)
            
            logger.info(f"Job {job_id} updated successfully")
            return job
            
        except Exception as e:
            logger.error(f"Job update failed: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Job update failed: {str(e)}")
    
    async def get_job(self, job_id: int, db: Session = None) -> Optional[Job]:
        """Get a job by ID."""
        if not db:
            db = next(get_db())
        
        return db.query(Job).filter(Job.id == job_id).first()
    
    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        company: Optional[str] = None,
        experience_level: Optional[str] = None,
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        remote_only: bool = False,
        limit: int = 50,
        offset: int = 0,
        db: Session = None
    ) -> List[Job]:
        """Search jobs with various filters."""
        if not db:
            db = next(get_db())
        
        # Build search query
        search_query = db.query(Job).filter(Job.is_active == True)
        
        if query:
            search_terms = query.split()
            for term in search_terms:
                search_query = search_query.filter(
                    or_(
                        Job.title.ilike(f"%{term}%"),
                        Job.description.ilike(f"%{term}%"),
                        Job.skills_required.ilike(f"%{term}%")
                    )
                )
        
        if location:
            search_query = search_query.filter(Job.location.ilike(f"%{location}%"))
        
        if company:
            search_query = search_query.filter(Job.company.ilike(f"%{company}%"))
        
        if experience_level:
            search_query = search_query.filter(Job.experience_level == experience_level)
        
        if salary_min:
            search_query = search_query.filter(Job.salary_min >= salary_min)
        
        if salary_max:
            search_query = search_query.filter(Job.salary_max <= salary_max)
        
        if remote_only:
            search_query = search_query.filter(
                or_(
                    Job.remote_work == True,
                    Job.location.ilike("%remote%")
                )
            )
        
        return search_query.order_by(desc(Job.posted_date)).offset(offset).limit(limit).all()
    
    async def get_skill_recommendations(
        self,
        user_id: int,
        target_roles: Optional[List[str]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get skill recommendations based on job market analysis."""
        try:
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get relevant jobs for analysis
            query = db.query(Job).filter(Job.is_active == True)
            
            if target_roles:
                role_filters = [Job.title.ilike(f"%{role}%") for role in target_roles]
                query = query.filter(or_(*role_filters))
            
            jobs = query.limit(100).all()
            
            if not jobs:
                return {"recommendations": [], "message": "No jobs found for analysis"}
            
            # Get Gemma service
            gemma_service = await self.get_gemma_service()
            
            # Analyze skill gaps and recommendations
            recommendation_result = await gemma_service.recommend_skills(
                user_profile=await self._prepare_user_profile(user),
                market_jobs=[await self._prepare_job_data(job) for job in jobs],
                target_roles=target_roles
            )
            
            if not recommendation_result.get("success"):
                raise HTTPException(status_code=500, detail="Skill recommendation failed")
            
            return {
                "recommendations": recommendation_result.get("skill_recommendations", []),
                "trending_skills": recommendation_result.get("trending_skills", []),
                "skill_gaps": recommendation_result.get("skill_gaps", []),
                "learning_paths": recommendation_result.get("learning_paths", []),
                "priority_skills": recommendation_result.get("priority_skills", []),
                "market_demand": recommendation_result.get("market_demand", {}),
                "analysis_metadata": {
                    "jobs_analyzed": len(jobs),
                    "target_roles": target_roles,
                    "analysis_date": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Skill recommendation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Skill recommendation failed: {str(e)}")
    
    # Private helper methods
    
    async def _structure_job_data(self, parsed_data: Dict, job_url: str, content: str) -> Dict[str, Any]:
        """Structure and validate parsed job data."""
        structured = {
            "title": parsed_data.get("title", "").strip(),
            "company": parsed_data.get("company", "").strip(),
            "location": parsed_data.get("location", "").strip(),
            "description": parsed_data.get("description", content[:2000]),
            "requirements": parsed_data.get("requirements", []),
            "skills_required": parsed_data.get("skills", []),
            "experience_level": parsed_data.get("experience_level", "").strip(),
            "employment_type": parsed_data.get("employment_type", "").strip(),
            "salary_min": parsed_data.get("salary_min"),
            "salary_max": parsed_data.get("salary_max"),
            "remote_work": parsed_data.get("remote_work", False),
            "url": job_url,
            "posted_date": datetime.utcnow(),
            "industry": parsed_data.get("industry", "").strip(),
            "company_size": parsed_data.get("company_size", "").strip(),
            "benefits": parsed_data.get("benefits", []),
            "keywords": extract_keywords(content)
        }
        
        return structured
    
    async def _extract_job_insights(self, job_data: Dict, content: str) -> Dict[str, Any]:
        """Extract additional insights from job posting."""
        insights = {
            "urgency_level": "normal",
            "company_culture": [],
            "growth_opportunities": [],
            "technology_stack": [],
            "team_size": None
        }
        
        # Simple heuristics for urgency
        urgent_keywords = ["urgent", "immediate", "asap", "quickly"]
        if any(keyword in content.lower() for keyword in urgent_keywords):
            insights["urgency_level"] = "high"
        
        return insights
    
    async def _prepare_user_profile(self, user: User) -> Dict[str, Any]:
        """Prepare user profile data for job matching."""
        return {
            "skills": user.skills or [],
            "experience": user.work_experience or [],
            "education": user.education or [],
            "certifications": user.certifications or [],
            "career_goals": user.career_goals or "",
            "preferred_location": user.preferred_location or "",
            "salary_expectation": user.salary_expectation,
            "remote_preference": user.remote_preference,
            "experience_years": user.experience_years or 0,
            "industry_preference": user.industry_preference or []
        }
    
    async def _prepare_job_data(self, job: Job) -> Dict[str, Any]:
        """Prepare job data for analysis."""
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "requirements": job.requirements or [],
            "skills_required": job.skills_required or [],
            "experience_level": job.experience_level,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "remote_work": job.remote_work,
            "industry": job.industry,
            "keywords": job.keywords or []
        }