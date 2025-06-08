#!/usr/bin/env python3
"""
Gemma 7B Model Server
Handles job matching, parsing, and relevance scoring
Port: 8002
"""

import asyncio
import logging
import os
import torch
import json
import re
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    GenerationConfig,
    pipeline
)
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model and tokenizer
model = None
tokenizer = None
text_generator = None

class JobMatchRequest(BaseModel):
    """Request model for job matching"""
    user_profile: Dict[str, Any] = Field(..., description="User profile and preferences")
    job_posting: Dict[str, Any] = Field(..., description="Job posting details")
    match_criteria: Optional[Dict[str, Any]] = Field(None, description="Custom matching criteria")

class JobParseRequest(BaseModel):
    """Request model for job posting parsing"""
    raw_job_text: str = Field(..., description="Raw job posting text")
    job_url: Optional[str] = Field(None, description="Source URL")
    company_name: Optional[str] = Field(None, description="Company name if known")

class BatchJobMatchRequest(BaseModel):
    """Request model for batch job matching"""
    user_profile: Dict[str, Any] = Field(..., description="User profile and preferences")
    job_postings: List[Dict[str, Any]] = Field(..., description="List of job postings")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

class JobMatchResponse(BaseModel):
    """Response model for job matching"""
    match_score: float = Field(..., description="Match score (0-100)")
    relevance_factors: Dict[str, float] = Field(..., description="Breakdown of relevance factors")
    missing_skills: List[str] = Field(..., description="Skills mentioned in job but not in profile")
    matching_skills: List[str] = Field(..., description="Skills that match between job and profile")
    recommendations: List[str] = Field(..., description="Recommendations for improving match")
    job_analysis: Dict[str, Any] = Field(..., description="Detailed job analysis")
    success: bool = Field(..., description="Analysis success status")

class JobParseResponse(BaseModel):
    """Response model for job parsing"""
    structured_data: Dict[str, Any] = Field(..., description="Parsed job posting data")
    extracted_skills: List[str] = Field(..., description="Extracted required skills")
    job_category: str = Field(..., description="Inferred job category")
    seniority_level: str = Field(..., description="Inferred seniority level")
    salary_info: Dict[str, Any] = Field(..., description="Extracted salary information")
    requirements: List[str] = Field(..., description="Parsed job requirements")
    responsibilities: List[str] = Field(..., description="Parsed job responsibilities")
    success: bool = Field(..., description="Parsing success status")

class BatchJobMatchResponse(BaseModel):
    """Response model for batch job matching"""
    matches: List[Dict[str, Any]] = Field(..., description="Ranked job matches")
    total_analyzed: int = Field(..., description="Total jobs analyzed")
    processing_time: float = Field(..., description="Processing time in seconds")
    success: bool = Field(..., description="Batch processing success status")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    memory_usage: Optional[str]
    timestamp: str

async def load_model():
    """Load Gemma 7B model and tokenizer"""
    global model, tokenizer, text_generator
    
    try:
        logger.info("Loading Gemma 7B model...")
        
        model_name = "google/gemma-7b-it"
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            padding_side="left"
        )
        
        # Add pad token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with optimizations for MacBook Air M4
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            load_in_8bit=True  # Use quantization to save memory
        )
        
        # Move to MPS if available (Apple Silicon)
        if torch.backends.mps.is_available() and not torch.cuda.is_available():
            model = model.to("mps")
            logger.info("Model loaded on Apple Silicon MPS")
        elif torch.cuda.is_available():
            logger.info("Model loaded on CUDA")
        else:
            logger.info("Model loaded on CPU")
        
        # Create text generation pipeline
        text_generator = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_length=2048,
            temperature=0.3,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        logger.info("Gemma 7B model loaded successfully!")
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise

async def unload_model():
    """Cleanup model resources"""
    global model, tokenizer, text_generator
    
    try:
        if model is not None:
            del model
        if tokenizer is not None:
            del tokenizer
        if text_generator is not None:
            del text_generator
        
        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()
            
        logger.info("Model resources cleaned up")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    await load_model()
    yield
    # Shutdown
    await unload_model()

# Initialize FastAPI app
app = FastAPI(
    title="Gemma 7B Job Analysis Service",
    description="AI-powered job matching and parsing using Gemma 7B",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_job_match_prompt(user_profile: Dict[str, Any], job_posting: Dict[str, Any]) -> str:
    """Create prompt for job matching analysis"""
    
    prompt = f"""<start_of_turn>user
You are an expert job matching analyst. Analyze how well a candidate's profile matches a job posting and provide a detailed assessment.

**Candidate Profile:**
- Name: {user_profile.get('name', 'Not provided')}
- Current Role: {user_profile.get('current_role', 'Not provided')}
- Experience Level: {user_profile.get('experience_years', 'Not provided')} years
- Skills: {', '.join(user_profile.get('skills', []))}
- Education: {user_profile.get('education', [])}
- Previous Experience: {user_profile.get('experience', [])}
- Certifications: {user_profile.get('certifications', [])}
- Preferred Salary: {user_profile.get('salary_expectation', 'Not specified')}
- Location Preference: {user_profile.get('location_preference', 'Not specified')}

**Job Posting:**
- Title: {job_posting.get('title', 'Not provided')}
- Company: {job_posting.get('company', 'Not provided')}
- Location: {job_posting.get('location', 'Not provided')}
- Salary Range: {job_posting.get('salary', 'Not provided')}
- Required Skills: {job_posting.get('required_skills', [])}
- Preferred Skills: {job_posting.get('preferred_skills', [])}
- Experience Required: {job_posting.get('experience_required', 'Not provided')}
- Education Required: {job_posting.get('education_required', 'Not provided')}
- Job Description: {job_posting.get('description', 'Not provided')}
- Requirements: {job_posting.get('requirements', 'Not provided')}

Please provide a comprehensive analysis in the following JSON format:
{{
    "match_score": <score from 0-100>,
    "relevance_factors": {{
        "skills_match": <score 0-100>,
        "experience_match": <score 0-100>,
        "education_match": <score 0-100>,
        "location_match": <score 0-100>,
        "salary_match": <score 0-100>
    }},
    "matching_skills": [<list of skills that match>],
    "missing_skills": [<list of required skills candidate lacks>],
    "recommendations": [<list of recommendations to improve candidacy>],
    "job_analysis": {{
        "seniority_level": "<junior/mid/senior/executive>",
        "job_category": "<category>",
        "key_responsibilities": [<main responsibilities>],
        "growth_potential": "<assessment>",
        "company_fit": "<assessment>"
    }}
}}

Focus on practical, actionable insights and be specific in your analysis.
<end_of_turn>
<start_of_turn>model
"""
    return prompt

def create_job_parse_prompt(raw_job_text: str, company_name: Optional[str] = None) -> str:
    """Create prompt for job posting parsing"""
    
    prompt = f"""<start_of_turn>user
You are an expert job posting parser. Extract structured information from the following job posting text.

**Company:** {company_name or 'Not specified'}

**Job Posting Text:**
{raw_job_text}

Please extract and structure the information in the following JSON format:
{{
    "structured_data": {{
        "title": "<job title>",
        "company": "<company name>",
        "location": "<location>",
        "job_type": "<full-time/part-time/contract/etc>",
        "remote_option": "<yes/no/hybrid>",
        "posted_date": "<date if available>",
        "application_deadline": "<deadline if available>"
    }},
    "salary_info": {{
        "min_salary": <minimum salary number or null>,
        "max_salary": <maximum salary number or null>,
        "currency": "<currency>",
        "period": "<hourly/monthly/yearly>",
        "benefits": [<list of benefits mentioned>]
    }},
    "requirements": [<list of hard requirements>],
    "responsibilities": [<list of key responsibilities>],
    "extracted_skills": [<list of technical and soft skills mentioned>],
    "experience_required": {{
        "min_years": <minimum years or null>,
        "max_years": <maximum years or null>,
        "level": "<junior/mid/senior/executive>"
    }},
    "education_required": [<education requirements>],
    "job_category": "<category like 'Software Development', 'Marketing', etc>",
    "seniority_level": "<junior/mid/senior/executive>",
    "company_description": "<company description if available>",
    "application_process": "<how to apply if specified>"
}}

Be thorough but accurate. If information is not available, use null or empty arrays as appropriate.
<end_of_turn>
<start_of_turn>model
"""
    return prompt

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extract JSON from model response"""
    try:
        # Try to find JSON in the response
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        if matches:
            # Try to parse the largest JSON-like string
            for match in sorted(matches, key=len, reverse=True):
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # If no valid JSON found, return a default structure
        logger.warning("Could not extract valid JSON from response")
        return {}
        
    except Exception as e:
        logger.error(f"Error extracting JSON: {str(e)}")
        return {}

async def analyze_job_match(request: JobMatchRequest) -> JobMatchResponse:
    """Analyze job match using Gemma 7B"""
    
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create prompt
        prompt = create_job_match_prompt(request.user_profile, request.job_posting)
        
        logger.info(f"Analyzing job match for {request.user_profile.get('name', 'user')}")
        
        # Generate response
        response = text_generator(
            prompt,
            max_new_tokens=1000,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_text = response[0]['generated_text'].strip()
        
        # Extract JSON from response
        analysis = extract_json_from_response(generated_text)
        
        # Validate and provide defaults
        match_score = analysis.get('match_score', 50.0)
        relevance_factors = analysis.get('relevance_factors', {
            'skills_match': 50.0,
            'experience_match': 50.0,
            'education_match': 50.0,
            'location_match': 50.0,
            'salary_match': 50.0
        })
        matching_skills = analysis.get('matching_skills', [])
        missing_skills = analysis.get('missing_skills', [])
        recommendations = analysis.get('recommendations', [])
        job_analysis = analysis.get('job_analysis', {})
        
        logger.info(f"Job match analysis completed with score: {match_score}")
        
        return JobMatchResponse(
            match_score=match_score,
            relevance_factors=relevance_factors,
            missing_skills=missing_skills,
            matching_skills=matching_skills,
            recommendations=recommendations,
            job_analysis=job_analysis,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error analyzing job match: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Job analysis failed: {str(e)}")

async def parse_job_posting(request: JobParseRequest) -> JobParseResponse:
    """Parse job posting using Gemma 7B"""
    
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create prompt
        prompt = create_job_parse_prompt(request.raw_job_text, request.company_name)
        
        logger.info("Parsing job posting")
        
        # Generate response
        response = text_generator(
            prompt,
            max_new_tokens=1200,
            temperature=0.2,
            top_p=0.9,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_text = response[0]['generated_text'].strip()
        
        # Extract JSON from response
        parsed_data = extract_json_from_response(generated_text)
        
        # Extract and validate fields
        structured_data = parsed_data.get('structured_data', {})
        extracted_skills = parsed_data.get('extracted_skills', [])
        job_category = parsed_data.get('job_category', 'General')
        seniority_level = parsed_data.get('seniority_level', 'mid')
        salary_info = parsed_data.get('salary_info', {})
        requirements = parsed_data.get('requirements', [])
        responsibilities = parsed_data.get('responsibilities', [])
        
        logger.info(f"Job posting parsed successfully")
        
        return JobParseResponse(
            structured_data=structured_data,
            extracted_skills=extracted_skills,
            job_category=job_category,
            seniority_level=seniority_level,
            salary_info=salary_info,
            requirements=requirements,
            responsibilities=responsibilities,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error parsing job posting: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Job parsing failed: {str(e)}")

async def batch_analyze_jobs(request: BatchJobMatchRequest) -> BatchJobMatchResponse:
    """Perform batch job matching"""
    
    start_time = datetime.now()
    matches = []
    
    try:
        logger.info(f"Starting batch analysis of {len(request.job_postings)} jobs")
        
        for i, job_posting in enumerate(request.job_postings):
            try:
                # Create individual match request
                match_request = JobMatchRequest(
                    user_profile=request.user_profile,
                    job_posting=job_posting
                )
                
                # Analyze match
                match_result = await analyze_job_match(match_request)
                
                # Add to results
                job_match = {
                    'job_id': job_posting.get('id', f'job_{i}'),
                    'job_title': job_posting.get('title', 'Unknown'),
                    'company': job_posting.get('company', 'Unknown'),
                    'match_score': match_result.match_score,
                    'relevance_factors': match_result.relevance_factors,
                    'matching_skills': match_result.matching_skills,
                    'missing_skills': match_result.missing_skills,
                    'recommendations': match_result.recommendations,
                    'job_analysis': match_result.job_analysis
                }
                
                matches.append(job_match)
                
            except Exception as e:
                logger.error(f"Error analyzing job {i}: {str(e)}")
                continue
        
        # Sort by match score
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Limit results
        if request.max_results:
            matches = matches[:request.max_results]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Batch analysis completed. Processed {len(matches)} jobs in {processing_time:.2f}s")
        
        return BatchJobMatchResponse(
            matches=matches,
            total_analyzed=len(request.job_postings),
            processing_time=processing_time,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@app.post("/match", response_model=JobMatchResponse)
async def match_job_endpoint(request: JobMatchRequest):
    """Analyze job match for a single job posting"""
    return await analyze_job_match(request)

@app.post("/parse", response_model=JobParseResponse)
async def parse_job_endpoint(request: JobParseRequest):
    """Parse a job posting into structured data"""
    return await parse_job_posting(request)

@app.post("/batch-match", response_model=BatchJobMatchResponse)
async def batch_match_jobs_endpoint(request: BatchJobMatchRequest):
    """Perform batch job matching"""
    return await batch_analyze_jobs(request)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    
    memory_usage = None
    if torch.cuda.is_available():
        memory_usage = f"{torch.cuda.memory_allocated() / 1024**3:.2f}GB"
    elif torch.backends.mps.is_available():
        memory_usage = f"{torch.mps.current_allocated_memory() / 1024**3:.2f}GB"
    
    return HealthResponse(
        status="healthy" if model is not None else "loading",
        model_loaded=model is not None,
        memory_usage=memory_usage,
        timestamp=datetime.now().isoformat()
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Gemma 7B Job Analysis Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "match": "/match",
            "parse": "/parse",
            "batch-match": "/batch-match",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    # Configure uvicorn
    uvicorn.run(
        "model_server:app",
        host="0.0.0.0",
        port=8002,
        log_level="info",
        access_log=True
    )