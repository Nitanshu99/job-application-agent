#!/usr/bin/env python3
"""
Phi-3 Mini Model Server
Handles document generation (resumes and cover letters)
Port: 8001
"""

import asyncio
import logging
import os
import torch
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
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

class DocumentRequest(BaseModel):
    """Request model for document generation"""
    user_profile: Dict[str, Any] = Field(..., description="User profile information")
    job_description: Dict[str, Any] = Field(..., description="Job posting details")
    document_type: str = Field(..., description="Type of document: 'resume' or 'cover_letter'")
    template_style: Optional[str] = Field("professional", description="Template style")
    additional_requirements: Optional[str] = Field(None, description="Additional customization requirements")

class DocumentResponse(BaseModel):
    """Response model for document generation"""
    document_content: str = Field(..., description="Generated document content")
    document_type: str = Field(..., description="Type of document generated")
    metadata: Dict[str, Any] = Field(..., description="Generation metadata")
    success: bool = Field(..., description="Generation success status")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    memory_usage: Optional[str]
    timestamp: str

async def load_model():
    """Load Phi-3 Mini model and tokenizer"""
    global model, tokenizer, text_generator
    
    try:
        logger.info("Loading Phi-3 Mini model...")
        
        model_name = "microsoft/Phi-3-mini-4k-instruct"
        
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
        )
        
        # Move to MPS if available (Apple Silicon)
        if torch.backends.mps.is_available():
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
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        logger.info("Phi-3 Mini model loaded successfully!")
        
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
    title="Phi-3 Mini Document Generation Service",
    description="AI-powered resume and cover letter generation using Phi-3 Mini",
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

def create_resume_prompt(user_profile: Dict[str, Any], job_description: Dict[str, Any]) -> str:
    """Create prompt for resume generation"""
    
    prompt = f"""
<|system|>
You are an expert resume writer. Create a professional, ATS-friendly resume tailored to the specific job posting. Focus on relevant skills, experiences, and achievements that match the job requirements.
<|end|>

<|user|>
Create a professional resume for the following candidate applying to this job:

**Job Information:**
- Title: {job_description.get('title', 'Not specified')}
- Company: {job_description.get('company', 'Not specified')}
- Requirements: {job_description.get('requirements', 'Not specified')}
- Description: {job_description.get('description', 'Not specified')}

**Candidate Profile:**
- Name: {user_profile.get('name', 'John Doe')}
- Email: {user_profile.get('email', 'john.doe@email.com')}
- Phone: {user_profile.get('phone', '(555) 123-4567')}
- Location: {user_profile.get('location', 'City, State')}
- Experience: {user_profile.get('experience', [])}
- Education: {user_profile.get('education', [])}
- Skills: {user_profile.get('skills', [])}
- Certifications: {user_profile.get('certifications', [])}

Please create a resume that:
1. Highlights relevant experience and skills for this specific role
2. Uses action verbs and quantified achievements
3. Is formatted professionally
4. Passes ATS systems
5. Is concise but comprehensive

Format the response as a clean, structured resume.
<|end|>

<|assistant|>
"""
    return prompt

def create_cover_letter_prompt(user_profile: Dict[str, Any], job_description: Dict[str, Any]) -> str:
    """Create prompt for cover letter generation"""
    
    prompt = f"""
<|system|>
You are an expert cover letter writer. Create a compelling, personalized cover letter that demonstrates genuine interest in the role and company while highlighting the candidate's most relevant qualifications.
<|end|>

<|user|>
Write a professional cover letter for the following candidate applying to this job:

**Job Information:**
- Title: {job_description.get('title', 'Not specified')}
- Company: {job_description.get('company', 'Not specified')}
- Requirements: {job_description.get('requirements', 'Not specified')}
- Description: {job_description.get('description', 'Not specified')}
- Company Culture: {job_description.get('culture', 'Not specified')}

**Candidate Profile:**
- Name: {user_profile.get('name', 'John Doe')}
- Current Role: {user_profile.get('current_role', 'Professional')}
- Experience: {user_profile.get('experience', [])}
- Skills: {user_profile.get('skills', [])}
- Achievements: {user_profile.get('achievements', [])}
- Why interested: {user_profile.get('motivation', 'Career growth opportunity')}

Please create a cover letter that:
1. Shows genuine interest in the company and role
2. Highlights 2-3 most relevant experiences/achievements
3. Demonstrates knowledge of the company
4. Maintains professional yet personable tone
5. Includes a strong call to action
6. Is 3-4 paragraphs in length

Format as a proper business letter.
<|end|>

<|assistant|>
"""
    return prompt

async def generate_document(request: DocumentRequest) -> DocumentResponse:
    """Generate document using Phi-3 Mini"""
    
    if text_generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Create appropriate prompt based on document type
        if request.document_type.lower() == "resume":
            prompt = create_resume_prompt(request.user_profile, request.job_description)
        elif request.document_type.lower() == "cover_letter":
            prompt = create_cover_letter_prompt(request.user_profile, request.job_description)
        else:
            raise HTTPException(status_code=400, detail="Invalid document type. Use 'resume' or 'cover_letter'")
        
        # Generate text
        logger.info(f"Generating {request.document_type} for {request.user_profile.get('name', 'user')}")
        
        # Configure generation parameters
        generation_config = GenerationConfig(
            max_new_tokens=1500,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
        
        # Generate response
        response = text_generator(
            prompt,
            max_new_tokens=1500,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id
        )
        
        generated_text = response[0]['generated_text'].strip()
        
        # Clean up the response
        if "<|assistant|>" in generated_text:
            generated_text = generated_text.split("<|assistant|>")[-1].strip()
        
        # Create metadata
        metadata = {
            "generation_time": datetime.now().isoformat(),
            "model": "Phi-3-mini-4k-instruct",
            "template_style": request.template_style,
            "job_title": request.job_description.get('title', 'Unknown'),
            "company": request.job_description.get('company', 'Unknown'),
            "user_name": request.user_profile.get('name', 'Unknown')
        }
        
        logger.info(f"Successfully generated {request.document_type}")
        
        return DocumentResponse(
            document_content=generated_text,
            document_type=request.document_type,
            metadata=metadata,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error generating document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")

@app.post("/generate", response_model=DocumentResponse)
async def generate_document_endpoint(request: DocumentRequest, background_tasks: BackgroundTasks):
    """Generate resume or cover letter"""
    return await generate_document(request)

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
        "service": "Phi-3 Mini Document Generation Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "generate": "/generate",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    # Configure uvicorn
    uvicorn.run(
        "model_server:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True
    )