#!/usr/bin/env python3
"""
Mistral 7B Model Server
Handles application automation, form filling, and application strategy
Port: 8003
"""

import asyncio
import logging
import os
import torch
import json
import re
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

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

class ApplicationStrategy(str, Enum):
    """Application strategy types"""
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    TARGETED = "targeted"

class ApplicationRequest(BaseModel):
    """Request model for application automation"""
    user_profile: Dict[str, Any] = Field(..., description="User profile data")
    job_posting: Dict[str, Any] = Field(..., description="Job posting details")
    resume_content: str = Field(..., description="Generated resume content")
    cover_letter_content: str = Field(..., description="Generated cover letter content")
    application_form_fields: Dict[str, Any] = Field(..., description="Application form fields")
    strategy: ApplicationStrategy = Field(ApplicationStrategy.STANDARD, description="Application strategy")
    custom_instructions: Optional[str] = Field(None, description="Custom application instructions")

class FormFieldRequest(BaseModel):
    """Request model for form field filling"""
    field_description: str = Field(..., description="Description of the form field")
    field_type: str = Field(..., description="Type of field (text, dropdown, checkbox, etc.)")
    available_options: Optional[List[str]] = Field(None, description="Available options for dropdown/checkbox")
    user_profile: Dict[str, Any] = Field(..., description="User profile data")
    job_context: Dict[str, Any] = Field(..., description="Job posting context")

class ApplicationPlanRequest(BaseModel):
    """Request model for application plan generation"""
    user_profile: Dict[str, Any] = Field(..., description="User profile data")
    job_posting: Dict[str, Any] = Field(..., description="Job posting details")
    application_deadline: Optional[str] = Field(None, description="Application deadline")
    priority_level: Optional[str] = Field("medium", description="Priority level: low, medium, high")

class ApplicationResponse(BaseModel):
    """Response model for application automation"""
    application_plan: Dict[str, Any] = Field(..., description="Step-by-step application plan")
    form_responses: Dict[str, str] = Field(..., description="Filled form fields")
    application_strategy: Dict[str, Any] = Field(..., description="Application strategy details")
    estimated_success_probability: float = Field(..., description="Estimated success probability (0-100)")
    recommendations: List[str] = Field(..., description="Application recommendations")
    follow_up_actions: List[Dict[str, Any]] = Field(..., description="Recommended follow-up actions")
    application_timeline: Dict[str, str] = Field(..., description="Application timeline")
    success: bool = Field(..., description="Processing success status")

class FormFieldResponse(BaseModel):
    """Response model for form field filling"""
    field_value: str = Field(..., description="Recommended field value")
    confidence: float = Field(..., description="Confidence in the response (0-100)")
    alternative_values: List[str] = Field(..., description="Alternative values if applicable")
    explanation: str = Field(..., description="Explanation for the chosen value")
    success: bool = Field(..., description="Processing success status")

class ApplicationPlanResponse(BaseModel):
    """Response model for application plan"""
    application_steps: List[Dict[str, Any]] = Field(..., description="Detailed application steps")
    timeline: Dict[str, str] = Field(..., description="Application timeline")
    preparation_tasks: List[str] = Field(..., description="Tasks to complete before applying")
    success_factors: List[str] = Field(..., description="Key factors for success")
    risk_assessment: Dict[str, Any] = Field(..., description="Application risks and mitigation")
    estimated_time: str = Field(..., description="Estimated time to complete application")
    success: bool = Field(..., description="Planning success status")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    memory_usage: Optional[str]
    timestamp: str

async def load_model():
    """Load Mistral 7B model and tokenizer"""
    global model, tokenizer, text_generator
    
    try:
        logger.info("Loading Mistral 7B model...")
        
        model_name = "mistralai/Mistral-7B-Instruct-v0.3"
        
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
            temperature=0.4,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        logger.info("Mistral 7B model loaded successfully!")
        
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
    title="Mistral 7B Application Automation Service",
    description="AI-powered job application automation using Mistral 7B Instruct",
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

def create_application_prompt(request: ApplicationRequest) -> str:
    """Create prompt for application automation"""
    
    prompt = f"""<s>[INST] You are an expert job application strategist. Create a comprehensive application plan and fill out form fields for a job application.

**User Profile:**
- Name: {request.user_profile.get('name', 'Not provided')}
- Current Role: {request.user_profile.get('current_role', 'Not provided')}
- Experience: {request.user_profile.get('experience_years', 'Not provided')} years
- Skills: {', '.join(request.user_profile.get('skills', []))}
- Education: {request.user_profile.get('education', [])}
- Contact: {request.user_profile.get('email', 'Not provided')}
- Phone: {request.user_profile.get('phone', 'Not provided')}
- Location: {request.user_profile.get('location', 'Not provided')}

**Job Details:**
- Title: {request.job_posting.get('title', 'Not provided')}
- Company: {request.job_posting.get('company', 'Not provided')}
- Location: {request.job_posting.get('location', 'Not provided')}
- Requirements: {request.job_posting.get('requirements', 'Not provided')}
- Description: {request.job_posting.get('description', 'Not provided')}

**Application Form Fields:**
{json.dumps(request.application_form_fields, indent=2)}

**Strategy:** {request.strategy.value}

**Custom Instructions:** {request.custom_instructions or 'None'}

Please provide a comprehensive response in JSON format:
{{
    "application_plan": {{
        "steps": [<ordered list of application steps>],
        "key_messaging": "<main message to convey>",
        "differentiation_strategy": "<how to stand out>"
    }},
    "form_responses": {{
        <field_name>: "<appropriate response for each form field>"
    }},
    "application_strategy": {{
        "approach": "<application approach>",
        "timing": "<when to apply>",
        "follow_up": "<follow-up strategy>"
    }},
    "estimated_success_probability": <percentage 0-100>,
    "recommendations": [<list of recommendations>],
    "follow_up_actions": [
        {{
            "action": "<action description>",
            "timing": "<when to do it>",
            "priority": "<high/medium/low>"
        }}
    ],
    "application_timeline": {{
        "preparation": "<time needed for prep>",
        "application": "<time to complete application>",
        "follow_up": "<follow-up timeline>"
    }}
}}

Focus on professional, authentic responses that highlight the candidate's strengths while being honest about their profile. [/INST]"""
    
    return prompt

def create_form_field_prompt(request: FormFieldRequest) -> str:
    """Create prompt for form field filling"""
    
    prompt = f"""<s>[INST] You are an expert at filling job application forms. Provide the most appropriate response for this form field.

**Form Field Details:**
- Field Description: {request.field_description}
- Field Type: {request.field_type}
- Available Options: {request.available_options or 'N/A'}

**User Profile:**
- Name: {request.user_profile.get('name', 'Not provided')}
- Experience: {request.user_profile.get('experience_years', 'Not provided')} years
- Skills: {', '.join(request.user_profile.get('skills', []))}
- Education: {request.user_profile.get('education', [])}
- Current Role: {request.user_profile.get('current_role', 'Not provided')}

**Job Context:**
- Title: {request.job_context.get('title', 'Not provided')}
- Company: {request.job_context.get('company', 'Not provided')}
- Requirements: {request.job_context.get('requirements', 'Not provided')}

Provide your response in JSON format:
{{
    "field_value": "<most appropriate value for this field>",
    "confidence": <confidence level 0-100>,
    "alternative_values": [<alternative options if applicable>],
    "explanation": "<brief explanation for your choice>"
}}

Be honest and accurate based on the user's profile. If the user doesn't meet a requirement, be truthful but position positively. [/INST]"""
    
    return prompt

def create_application_plan_prompt(request: ApplicationPlanRequest) -> str:
    """Create prompt for application plan generation"""
    
    prompt = f"""<s>[INST] You are an expert career strategist. Create a detailed application plan for this job opportunity.

**User Profile:**
- Name: {request.user_profile.get('name', 'Not provided')}
- Current Role: {request.user_profile.get('current_role', 'Not provided')}
- Experience: {request.user_profile.get('experience_years', 'Not provided')} years
- Skills: {', '.join(request.user_profile.get('skills', []))}
- Career Goals: {request.user_profile.get('career_goals', 'Not provided')}

**Job Opportunity:**
- Title: {request.job_posting.get('title', 'Not provided')}
- Company: {request.job_posting.get('company', 'Not provided')}
- Requirements: {request.job_posting.get('requirements', 'Not provided')}
- Application Deadline: {request.application_deadline or 'Not specified'}
- Priority Level: {request.priority_level}

Create a comprehensive application plan in JSON format:
{{
    "application_steps": [
        {{
            "step": "<step number>",
            "action": "<what to do>",
            "description": "<detailed description>",
            "estimated_time": "<time needed>",
            "dependencies": [<what needs to be done first>]
        }}
    ],
    "timeline": {{
        "start_date": "<when to start>",
        "application_date": "<target application date>",
        "follow_up_dates": [<follow-up schedule>]
    }},
    "preparation_tasks": [<tasks to complete before applying>],
    "success_factors": [<key factors that will make this application successful>],
    "risk_assessment": {{
        "risks": [<potential risks or challenges>],
        "mitigation": [<how to address each risk>],
        "backup_plans": [<alternative approaches>]
    }},
    "estimated_time": "<total time commitment>"
}}

Focus on creating a realistic, actionable plan that maximizes the candidate's chances of success. [/INST]"""
    
    return prompt

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extract JSON from model response"""
    try:
        # Clean up the response text
        cleaned_text = response_text.strip()
        
        # Find JSON content between braces
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, cleaned_text, re.DOTALL)
        
        if matches:
            # Try to parse the largest JSON-like string
            for match in sorted(matches, key=len, reverse=True):
                try:
                    # Clean common formatting issues
                    match = match.replace('\n', ' ').replace('\t', ' ')
                    # Remove extra spaces
                    match = re.sub(r'\s+', ' ', match)
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # If no valid JSON found, return empty dict
        logger.warning("Could not extract valid JSON from response")
        return {}
        
    except Exception as e:
        logger.error(f"Error extracting JSON: {str(e)}")
        return {}

async def process_application(request: ApplicationRequest) -> ApplicationResponse:
    """Process job application using Mistral 7B"""
    
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create prompt
        prompt = create_application_prompt(request)
        
        logger.info(f"Processing application for {request.user_profile.get('name', 'user')}")
        
        # Generate response
        response = text_generator(
            prompt,
            max_new_tokens=1200,
            temperature=0.4,
            top_p=0.9,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_text = response[0]['generated_text'].strip()
        
        # Extract JSON from response
        analysis = extract_json_from_response(generated_text)
        
        # Validate and provide defaults
        application_plan = analysis.get('application_plan', {
            'steps': ['Review job requirements', 'Submit application', 'Follow up'],
            'key_messaging': 'Strong candidate match',
            'differentiation_strategy': 'Highlight unique skills'
        })
        
        form_responses = analysis.get('form_responses', {})
        application_strategy = analysis.get('application_strategy', {
            'approach': 'standard',
            'timing': 'immediate',
            'follow_up': 'weekly check-ins'
        })
        
        estimated_success_probability = analysis.get('estimated_success_probability', 60.0)
        recommendations = analysis.get('recommendations', ['Submit application promptly'])
        follow_up_actions = analysis.get('follow_up_actions', [])
        application_timeline = analysis.get('application_timeline', {
            'preparation': '1-2 hours',
            'application': '30 minutes',
            'follow_up': '1 week'
        })
        
        logger.info(f"Application processing completed with {estimated_success_probability}% success probability")
        
        return ApplicationResponse(
            application_plan=application_plan,
            form_responses=form_responses,
            application_strategy=application_strategy,
            estimated_success_probability=estimated_success_probability,
            recommendations=recommendations,
            follow_up_actions=follow_up_actions,
            application_timeline=application_timeline,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error processing application: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Application processing failed: {str(e)}")

async def fill_form_field(request: FormFieldRequest) -> FormFieldResponse:
    """Fill individual form field using Mistral 7B"""
    
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create prompt
        prompt = create_form_field_prompt(request)
        
        logger.info(f"Filling form field: {request.field_description}")
        
        # Generate response
        response = text_generator(
            prompt,
            max_new_tokens=400,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_text = response[0]['generated_text'].strip()
        
        # Extract JSON from response
        result = extract_json_from_response(generated_text)
        
        # Validate and provide defaults
        field_value = result.get('field_value', 'N/A')
        confidence = result.get('confidence', 70.0)
        alternative_values = result.get('alternative_values', [])
        explanation = result.get('explanation', 'Standard response based on profile')
        
        logger.info(f"Form field filled with confidence: {confidence}%")
        
        return FormFieldResponse(
            field_value=field_value,
            confidence=confidence,
            alternative_values=alternative_values,
            explanation=explanation,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error filling form field: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Form field filling failed: {str(e)}")

async def create_application_plan(request: ApplicationPlanRequest) -> ApplicationPlanResponse:
    """Create application plan using Mistral 7B"""
    
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create prompt
        prompt = create_application_plan_prompt(request)
        
        logger.info(f"Creating application plan for {request.job_posting.get('title', 'job')}")
        
        # Generate response
        response = text_generator(
            prompt,
            max_new_tokens=1000,
            temperature=0.4,
            top_p=0.9,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_text = response[0]['generated_text'].strip()
        
        # Extract JSON from response
        plan = extract_json_from_response(generated_text)
        
        # Validate and provide defaults
        application_steps = plan.get('application_steps', [])
        timeline = plan.get('timeline', {})
        preparation_tasks = plan.get('preparation_tasks', [])
        success_factors = plan.get('success_factors', [])
        risk_assessment = plan.get('risk_assessment', {})
        estimated_time = plan.get('estimated_time', '2-3 hours')
        
        logger.info(f"Application plan created successfully")
        
        return ApplicationPlanResponse(
            application_steps=application_steps,
            timeline=timeline,
            preparation_tasks=preparation_tasks,
            success_factors=success_factors,
            risk_assessment=risk_assessment,
            estimated_time=estimated_time,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error creating application plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Application planning failed: {str(e)}")

@app.post("/apply", response_model=ApplicationResponse)
async def apply_job_endpoint(request: ApplicationRequest):
    """Process complete job application"""
    return await process_application(request)

@app.post("/fill-field", response_model=FormFieldResponse)
async def fill_field_endpoint(request: FormFieldRequest):
    """Fill individual form field"""
    return await fill_form_field(request)

@app.post("/plan", response_model=ApplicationPlanResponse)
async def create_plan_endpoint(request: ApplicationPlanRequest):
    """Create application plan"""
    return await create_application_plan(request)

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
        "service": "Mistral 7B Application Automation Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "apply": "/apply",
            "fill-field": "/fill-field",
            "plan": "/plan",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    # Configure uvicorn
    uvicorn.run(
        "model_server:app",
        host="0.0.0.0",
        port=8003,
        log_level="info",
        access_log=True
    )