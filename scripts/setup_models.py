#!/usr/bin/env python3
"""
Model setup utility for the Job Automation System.
Downloads, configures, and manages LLM models (Phi-3, Gemma, Mistral).
"""

import os
import sys
import logging
import subprocess
import shutil
import hashlib
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import click
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
import yaml
import docker
from huggingface_hub import snapshot_download, login, HfApi
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Setup rich console
console = Console()
logger = logging.getLogger(__name__)


class ModelConfig:
    """Configuration for LLM models."""
    
    MODELS = {
        "phi3": {
            "name": "Phi-3 Mini",
            "hf_model_id": "microsoft/Phi-3-mini-4k-instruct",
            "local_path": "models/phi3/model_files",
            "service_port": 8001,
            "memory_requirement": "2GB",
            "description": "Microsoft Phi-3 Mini - optimized for document generation",
            "use_case": "Resume and cover letter generation",
            "quantization": True,
            "torch_dtype": "float16"
        },
        "gemma": {
            "name": "Gemma 7B",
            "hf_model_id": "google/gemma-7b-it",
            "local_path": "models/gemma/model_files", 
            "service_port": 8002,
            "memory_requirement": "4GB",
            "description": "Google Gemma 7B - intelligent job matching and analysis",
            "use_case": "Job parsing and relevance scoring",
            "quantization": True,
            "torch_dtype": "float16"
        },
        "mistral": {
            "name": "Mistral 7B Instruct",
            "hf_model_id": "mistralai/Mistral-7B-Instruct-v0.2",
            "local_path": "models/mistral/model_files",
            "service_port": 8003,
            "memory_requirement": "3GB", 
            "description": "Mistral 7B Instruct - automated application filling",
            "use_case": "Application form automation and submission",
            "quantization": True,
            "torch_dtype": "float16"
        }
    }


class ModelManager:
    """Manager for downloading and setting up LLM models."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.models_dir = self.base_path / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Initialize Docker client
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not connect to Docker: {e}")
        
        # Initialize HuggingFace API
        self.hf_api = HfApi()

    def check_system_requirements(self) -> Dict[str, bool]:
        """Check if system meets requirements for model setup."""
        requirements = {}
        
        # Check available disk space (need ~20GB)
        stat = shutil.disk_usage(self.base_path)
        free_gb = stat.free / (1024**3)
        requirements["disk_space"] = free_gb >= 20
        
        # Check available RAM
        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / (1024**3)
            requirements["memory"] = ram_gb >= 8
        except ImportError:
            requirements["memory"] = True  # Assume sufficient if can't check
        
        # Check Python version
        requirements["python_version"] = sys.version_info >= (3, 8)
        
        # Check PyTorch availability
        try:
            import torch
            requirements["pytorch"] = True
            requirements["cuda_available"] = torch.cuda.is_available()
            if torch.backends.mps.is_available():
                requirements["mps_available"] = True
            else:
                requirements["mps_available"] = False
        except ImportError:
            requirements["pytorch"] = False
            requirements["cuda_available"] = False
            requirements["mps_available"] = False
        
        # Check HuggingFace transformers
        try:
            import transformers
            requirements["transformers"] = True
        except ImportError:
            requirements["transformers"] = False
        
        # Check Docker
        requirements["docker"] = self.docker_client is not None
        
        return requirements

    def authenticate_huggingface(self, token: Optional[str] = None) -> bool:
        """Authenticate with HuggingFace Hub."""
        try:
            if token:
                login(token=token)
                console.print("✅ HuggingFace authentication successful", style="green")
                return True
            else:
                # Try to use existing token
                try:
                    whoami = self.hf_api.whoami()
                    console.print(f"✅ Already authenticated as: {whoami['name']}", style="green")
                    return True
                except Exception:
                    console.print("⚠️ HuggingFace authentication required for some models", style="yellow")
                    console.print("   Use --hf-token or run 'huggingface-cli login'", style="yellow")
                    return False
        except Exception as e:
            console.print(f"❌ HuggingFace authentication failed: {e}", style="red")
            return False

    def download_model(self, model_key: str, force: bool = False) -> bool:
        """Download a specific model from HuggingFace."""
        if model_key not in ModelConfig.MODELS:
            console.print(f"❌ Unknown model: {model_key}", style="red")
            return False
        
        model_config = ModelConfig.MODELS[model_key]
        local_path = self.base_path / model_config["local_path"]
        
        # Check if model already exists
        if local_path.exists() and not force:
            console.print(f"⚠️ Model {model_config['name']} already exists at {local_path}", style="yellow")
            console.print("   Use --force to re-download", style="yellow")
            return True
        
        try:
            console.print(f"📥 Downloading {model_config['name']}...", style="blue")
            console.print(f"   From: {model_config['hf_model_id']}", style="dim")
            console.print(f"   To: {local_path}", style="dim")
            
            # Create directory
            local_path.mkdir(parents=True, exist_ok=True)
            
            # Download with progress
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task(f"Downloading {model_config['name']}", total=100)
                
                def progress_callback(downloaded, total):
                    if total > 0:
                        progress.update(task, completed=downloaded, total=total)
                
                # Download model files
                snapshot_download(
                    repo_id=model_config["hf_model_id"],
                    local_dir=str(local_path),
                    local_dir_use_symlinks=False,
                    resume_download=True
                )
                
                progress.update(task, completed=100, total=100)
            
            console.print(f"✅ Successfully downloaded {model_config['name']}", style="green")
            
            # Verify download
            if self.verify_model(model_key):
                console.print(f"✅ Model verification passed", style="green")
                return True
            else:
                console.print(f"❌ Model verification failed", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Failed to download {model_config['name']}: {e}", style="red")
            return False

    def verify_model(self, model_key: str) -> bool:
        """Verify downloaded model integrity."""
        if model_key not in ModelConfig.MODELS:
            return False
        
        model_config = ModelConfig.MODELS[model_key]
        local_path = self.base_path / model_config["local_path"]
        
        try:
            # Check if required files exist
            required_files = ["config.json", "tokenizer.json", "tokenizer_config.json"]
            
            for file_name in required_files:
                file_path = local_path / file_name
                if not file_path.exists():
                    console.print(f"❌ Missing required file: {file_name}", style="red")
                    return False
            
            # Try to load tokenizer (quick test)
            tokenizer = AutoTokenizer.from_pretrained(str(local_path))
            if tokenizer is None:
                console.print(f"❌ Failed to load tokenizer", style="red")
                return False
            
            # Check model files
            model_files = list(local_path.glob("*.safetensors")) + list(local_path.glob("*.bin"))
            if not model_files:
                console.print(f"❌ No model weight files found", style="red")
                return False
            
            return True
            
        except Exception as e:
            console.print(f"❌ Model verification failed: {e}", style="red")
            return False

    def setup_model_environment(self, model_key: str) -> bool:
        """Setup environment and dependencies for a model."""
        if model_key not in ModelConfig.MODELS:
            return False
        
        model_config = ModelConfig.MODELS[model_key]
        model_dir = self.base_path / f"models/{model_key}"
        
        try:
            console.print(f"⚙️ Setting up environment for {model_config['name']}...", style="blue")
            
            # Create model server script if it doesn't exist
            server_script = model_dir / "model_server.py"
            if not server_script.exists():
                self.create_model_server_script(model_key)
            
            # Create Dockerfile if it doesn't exist
            dockerfile = model_dir / "Dockerfile"
            if not dockerfile.exists():
                self.create_dockerfile(model_key)
            
            # Create requirements.txt if it doesn't exist
            requirements_file = model_dir / "requirements.txt"
            if not requirements_file.exists():
                self.create_requirements_file(model_key)
            
            console.print(f"✅ Environment setup complete for {model_config['name']}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Environment setup failed: {e}", style="red")
            return False

    def create_model_server_script(self, model_key: str):
        """Create model server script."""
        model_config = ModelConfig.MODELS[model_key]
        model_dir = self.base_path / f"models/{model_key}"
        
        server_script = f'''#!/usr/bin/env python3
"""
{model_config['name']} Model Server
Serves the {model_config['name']} model via FastAPI for {model_config['use_case']}.
"""

import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import warnings
warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="{model_config['name']} Service", version="1.0.0")

# Global model and tokenizer
model = None
tokenizer = None

class GenerationRequest(BaseModel):
    text: str
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    do_sample: bool = True

class GenerationResponse(BaseModel):
    generated_text: str
    input_text: str
    model_name: str

@app.on_event("startup")
async def load_model():
    """Load model on startup."""
    global model, tokenizer
    
    try:
        logger.info("Loading {model_config['name']}...")
        
        model_path = os.getenv("MODEL_PATH", "./model_files")
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Configure quantization for memory efficiency
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.{model_config['torch_dtype']},
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        # Load model with quantization
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quantization_config if {str(model_config['quantization']).lower()} else None,
            device_map="auto",
            torch_dtype=torch.{model_config['torch_dtype']},
            trust_remote_code=True
        )
        
        logger.info("{model_config['name']} loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load model: {{e}}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {{
        "status": "healthy",
        "model": "{model_config['name']}",
        "model_loaded": model is not None,
        "tokenizer_loaded": tokenizer is not None,
        "use_case": "{model_config['use_case']}",
        "memory_requirement": "{model_config['memory_requirement']}"
    }}

@app.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest):
    """Generate text using the model."""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Tokenize input
        inputs = tokenizer(
            request.text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_length=request.max_length,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.do_sample,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode output
        generated_text = tokenizer.decode(
            outputs[0], 
            skip_special_tokens=True
        )
        
        # Remove input text from output
        generated_text = generated_text[len(request.text):].strip()
        
        return GenerationResponse(
            generated_text=generated_text,
            input_text=request.text,
            model_name="{model_config['name']}"
        )
        
    except Exception as e:
        logger.error(f"Generation failed: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port={model_config['service_port']},
        log_level="info"
    )
'''
        
        server_file = model_dir / "model_server.py"
        server_file.write_text(server_script)
        console.print(f"   ✅ Created server script: {server_file}", style="green")

    def create_dockerfile(self, model_key: str):
        """Create Dockerfile for model service."""
        model_config = ModelConfig.MODELS[model_key]
        model_dir = self.base_path / f"models/{model_key}"
        
        dockerfile_content = f'''# {model_config['name']} Model Service
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model files and server script
COPY model_files/ ./model_files/
COPY model_server.py .

# Set environment variables
ENV MODEL_PATH=./model_files
ENV PYTHONPATH=/app

# Expose port
EXPOSE {model_config['service_port']}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{model_config['service_port']}/health || exit 1

# Run the server
CMD ["python", "model_server.py"]
'''
        
        dockerfile = model_dir / "Dockerfile"
        dockerfile.write_text(dockerfile_content)
        console.print(f"   ✅ Created Dockerfile: {dockerfile}", style="green")

    def create_requirements_file(self, model_key: str):
        """Create requirements.txt for model service."""
        model_dir = self.base_path / f"models/{model_key}"
        
        # Base requirements for all models
        requirements = [
            "torch==2.1.1",
            "transformers==4.36.0",
            "accelerate==0.24.1",
            "tokenizers==0.15.0",
            "fastapi==0.104.1",
            "uvicorn==0.24.0",
            "pydantic==2.5.0",
            "bitsandbytes==0.41.3"
        ]
        
        # Model-specific requirements
        if model_key == "mistral":
            requirements.append("mistral-common==1.0.0")
        
        requirements_file = model_dir / "requirements.txt"
        requirements_file.write_text("\\n".join(requirements) + "\\n")
        console.print(f"   ✅ Created requirements: {requirements_file}", style="green")

    def build_docker_image(self, model_key: str, force: bool = False) -> bool:
        """Build Docker image for model service."""
        if not self.docker_client:
            console.print("❌ Docker not available", style="red")
            return False
        
        if model_key not in ModelConfig.MODELS:
            console.print(f"❌ Unknown model: {model_key}", style="red")
            return False
        
        model_config = ModelConfig.MODELS[model_key]
        model_dir = self.base_path / f"models/{model_key}"
        image_name = f"jobautomation-{model_key}:latest"
        
        try:
            # Check if image already exists
            if not force:
                try:
                    self.docker_client.images.get(image_name)
                    console.print(f"⚠️ Image {image_name} already exists", style="yellow")
                    console.print("   Use --force to rebuild", style="yellow")
                    return True
                except docker.errors.ImageNotFound:
                    pass
            
            console.print(f"🐳 Building Docker image for {model_config['name']}...", style="blue")
            
            # Build image
            image, build_logs = self.docker_client.images.build(
                path=str(model_dir),
                tag=image_name,
                rm=True,
                forcerm=True
            )
            
            console.print(f"✅ Successfully built Docker image: {image_name}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Failed to build Docker image: {e}", style="red")
            return False

    def get_model_status(self) -> Dict[str, Dict]:
        """Get status of all models."""
        status = {}
        
        for model_key, model_config in ModelConfig.MODELS.items():
            local_path = self.base_path / model_config["local_path"]
            
            model_status = {
                "name": model_config["name"],
                "downloaded": local_path.exists() and self.verify_model(model_key),
                "size": self.get_directory_size(local_path) if local_path.exists() else 0,
                "path": str(local_path),
                "use_case": model_config["use_case"],
                "memory_requirement": model_config["memory_requirement"]
            }
            
            # Check Docker image
            if self.docker_client:
                try:
                    image_name = f"jobautomation-{model_key}:latest"
                    self.docker_client.images.get(image_name)
                    model_status["docker_image"] = True
                except docker.errors.ImageNotFound:
                    model_status["docker_image"] = False
            else:
                model_status["docker_image"] = None
            
            status[model_key] = model_status
        
        return status

    def get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        if not path.exists():
            return 0
        
        total_size = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def format_size(self, size_bytes: int) -> str:
        """Format size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


def print_system_requirements(requirements: Dict[str, bool]):
    """Print system requirements check."""
    table = Table(title="System Requirements Check")
    table.add_column("Requirement", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")
    
    status_map = {True: "✅ Pass", False: "❌ Fail"}
    
    table.add_row("Disk Space (20GB+)", status_map[requirements["disk_space"]], 
                  "Required for model storage")
    table.add_row("Memory (8GB+)", status_map[requirements["memory"]], 
                  "Required for model loading")
    table.add_row("Python 3.8+", status_map[requirements["python_version"]], 
                  f"Current: {sys.version}")
    table.add_row("PyTorch", status_map[requirements["pytorch"]], 
                  "Required for model inference")
    table.add_row("CUDA Available", status_map[requirements["cuda_available"]], 
                  "Optional: GPU acceleration")
    table.add_row("MPS Available", status_map[requirements["mps_available"]], 
                  "Optional: Apple Silicon acceleration")
    table.add_row("Transformers", status_map[requirements["transformers"]], 
                  "Required for model loading")
    table.add_row("Docker", status_map[requirements["docker"]], 
                  "Required for containerization")
    
    console.print(table)


def print_model_status(status: Dict[str, Dict]):
    """Print model status table."""
    table = Table(title="Model Status")
    table.add_column("Model", style="cyan")
    table.add_column("Downloaded", style="green") 
    table.add_column("Size", style="blue")
    table.add_column("Docker Image", style="magenta")
    table.add_column("Use Case", style="dim")
    
    for model_key, model_info in status.items():
        downloaded = "✅ Yes" if model_info["downloaded"] else "❌ No"
        size = ModelManager().format_size(model_info["size"]) if model_info["size"] > 0 else "N/A"
        
        if model_info["docker_image"] is True:
            docker_status = "✅ Built"
        elif model_info["docker_image"] is False:
            docker_status = "❌ Missing"
        else:
            docker_status = "❓ Unknown"
        
        table.add_row(
            model_info["name"],
            downloaded,
            size,
            docker_status,
            model_info["use_case"]
        )
    
    console.print(table)


@click.group()
def cli():
    """Model setup and management for Job Automation System."""
    pass


@cli.command()
@click.option('--hf-token', help='HuggingFace token for authentication')
def check():
    """Check system requirements and model status."""
    console.print(Panel.fit("🔍 System Requirements & Model Status", style="bold blue"))
    
    manager = ModelManager()
    
    # Check requirements
    requirements = manager.check_system_requirements()
    print_system_requirements(requirements)
    
    # Authenticate with HuggingFace
    if not manager.authenticate_huggingface():
        console.print("⚠️ Some models may require HuggingFace authentication", style="yellow")
    
    # Check model status
    console.print()
    status = manager.get_model_status()
    print_model_status(status)


@cli.command()
@click.argument('models', nargs=-1)
@click.option('--all', is_flag=True, help='Download all models')
@click.option('--force', is_flag=True, help='Force re-download existing models')
@click.option('--hf-token', help='HuggingFace token for authentication')
def download(models: List[str], all: bool, force: bool, hf_token: Optional[str]):
    """Download specified models or all models."""
    
    manager = ModelManager()
    
    # Authenticate with HuggingFace
    manager.authenticate_huggingface(hf_token)
    
    # Determine which models to download
    if all:
        models_to_download = list(ModelConfig.MODELS.keys())
    elif models:
        models_to_download = models
    else:
        console.print("❌ Please specify models to download or use --all", style="red")
        return
    
    console.print(Panel.fit("📥 Model Download", style="bold blue"))
    
    # Download each model
    success_count = 0
    for model_key in models_to_download:
        if model_key not in ModelConfig.MODELS:
            console.print(f"❌ Unknown model: {model_key}", style="red")
            continue
        
        if manager.download_model(model_key, force=force):
            success_count += 1
    
    console.print(f"\\n✅ Successfully downloaded {success_count}/{len(models_to_download)} models", style="green")


@cli.command()
@click.argument('models', nargs=-1)
@click.option('--all', is_flag=True, help='Setup all models')
def setup(models: List[str], all: bool):
    """Setup model environments (create scripts, Dockerfiles, etc.)."""
    
    manager = ModelManager()
    
    # Determine which models to setup
    if all:
        models_to_setup = list(ModelConfig.MODELS.keys())
    elif models:
        models_to_setup = models
    else:
        console.print("❌ Please specify models to setup or use --all", style="red")
        return
    
    console.print(Panel.fit("⚙️ Model Environment Setup", style="bold blue"))
    
    # Setup each model
    success_count = 0
    for model_key in models_to_setup:
        if model_key not in ModelConfig.MODELS:
            console.print(f"❌ Unknown model: {model_key}", style="red")
            continue
        
        if manager.setup_model_environment(model_key):
            success_count += 1
    
    console.print(f"\\n✅ Successfully setup {success_count}/{len(models_to_setup)} models", style="green")


@cli.command()
@click.argument('models', nargs=-1)
@click.option('--all', is_flag=True, help='Build all model images')
@click.option('--force', is_flag=True, help='Force rebuild existing images')
def build(models: List[str], all: bool, force: bool):
    """Build Docker images for model services."""
    
    manager = ModelManager()
    
    if not manager.docker_client:
        console.print("❌ Docker not available", style="red")
        return
    
    # Determine which models to build
    if all:
        models_to_build = list(ModelConfig.MODELS.keys())
    elif models:
        models_to_build = models
    else:
        console.print("❌ Please specify models to build or use --all", style="red")
        return
    
    console.print(Panel.fit("🐳 Docker Image Build", style="bold blue"))
    
    # Build each model
    success_count = 0
    for model_key in models_to_build:
        if model_key not in ModelConfig.MODELS:
            console.print(f"❌ Unknown model: {model_key}", style="red")
            continue
        
        if manager.build_docker_image(model_key, force=force):
            success_count += 1
    
    console.print(f"\\n✅ Successfully built {success_count}/{len(models_to_build)} images", style="green")


@cli.command()
def status():
    """Show current status of all models."""
    
    manager = ModelManager()
    
    console.print(Panel.fit("📊 Model Status", style="bold blue"))
    
    status = manager.get_model_status()
    print_model_status(status)


@cli.command()
@click.option('--hf-token', help='HuggingFace token for authentication')
@click.option('--force', is_flag=True, help='Force re-download and rebuild')
def install_all(hf_token: Optional[str], force: bool):
    """Complete installation: download, setup, and build all models."""
    
    manager = ModelManager()
    
    console.print(Panel.fit("🚀 Complete Model Installation", style="bold blue"))
    
    # Check requirements first
    requirements = manager.check_system_requirements()
    print_system_requirements(requirements)
    
    # Check critical requirements
    critical_failed = not all([
        requirements["disk_space"],
        requirements["python_version"],
        requirements["pytorch"],
        requirements["transformers"]
    ])
    
    if critical_failed:
        console.print("❌ Critical requirements not met. Please fix before continuing.", style="red")
        return
    
    # Authenticate
    manager.authenticate_huggingface(hf_token)
    
    console.print("\\n🔄 Starting complete installation process...", style="blue")
    
    all_models = list(ModelConfig.MODELS.keys())
    
    # Step 1: Download all models
    console.print("\\n📥 Step 1: Downloading models...", style="blue")
    download_success = 0
    for model_key in all_models:
        if manager.download_model(model_key, force=force):
            download_success += 1
    
    # Step 2: Setup environments
    console.print("\\n⚙️ Step 2: Setting up environments...", style="blue")
    setup_success = 0
    for model_key in all_models:
        if manager.setup_model_environment(model_key):
            setup_success += 1
    
    # Step 3: Build Docker images
    console.print("\\n🐳 Step 3: Building Docker images...", style="blue")
    build_success = 0
    if manager.docker_client:
        for model_key in all_models:
            if manager.build_docker_image(model_key, force=force):
                build_success += 1
    else:
        console.print("   ⚠️ Skipping Docker builds (Docker not available)", style="yellow")
    
    # Final status
    console.print("\\n" + "="*60, style="green")
    console.print("🎉 Installation Complete!", style="bold green")
    console.print(f"   ✅ Downloaded: {download_success}/{len(all_models)} models", style="green")
    console.print(f"   ✅ Setup: {setup_success}/{len(all_models)} environments", style="green")
    if manager.docker_client:
        console.print(f"   ✅ Built: {build_success}/{len(all_models)} Docker images", style="green")
    console.print("="*60, style="green")
    
    # Show final status
    console.print()
    status = manager.get_model_status()
    print_model_status(status)


if __name__ == "__main__":
    cli()