# 🚀 AI-Powered Job Application Automation System

A comprehensive job application automation platform that generates personalized resumes and cover letters, scrapes job postings, and automates applications using local LLM models optimized for MacBook Air M4.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Project Structure](#-project-structure)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Contributing](#-contributing)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

## ✨ Features

- **🤖 AI-Powered Document Generation**: Generate tailored resumes and cover letters using Phi-3 Mini
- **🔍 Intelligent Job Matching**: Parse and match jobs using Gemma 7B with relevance scoring
- **📝 Automated Applications**: Fill and submit applications using Mistral 7B Instruct
- **👤 User Profile Management**: Comprehensive user profiles with experience, skills, and preferences
- **🌐 Custom Job Portal Integration**: Add and manage custom company career pages and job boards
- **📋 Smart Application Manager**: Track all job applications with duplicate prevention system
- **🔄 Application History**: Complete history of applied jobs with links, descriptions, and status
- **🚫 Duplicate Prevention**: Automatic detection and prevention of repeat applications
- **🐳 Dockerized Architecture**: Containerized services for easy deployment and scaling
- **📊 Application Tracking**: Monitor application status and success rates
- **🔒 Secure Data Storage**: Encrypted user data with PostgreSQL backend
- **📱 Responsive Web Interface**: Modern React frontend with TypeScript

## 🏗️ Architecture

The system uses a microservices architecture with sequential LLM usage to optimize resource consumption on MacBook Air M4:


### 📋 Requirements Files Explained

| File Location | Purpose | Size | Key Dependencies |
|---------------|---------|------|-----------------|
| `requirements.txt` | Root project tools & scripts | ~50MB | Click, Rich, PyYAML, Docker |
| `requirements-dev.txt` | Development & testing tools | ~100MB | Pytest, Black, MyPy, Sphinx |
| `backend/requirements.txt` | FastAPI backend dependencies | ~200MB | FastAPI, SQLAlchemy, Celery |
| `frontend/package.json` | React frontend dependencies | ~150MB | React, TypeScript, Next.js |
| `models/phi3/requirements.txt` | Phi-3 Mini model service | ~1.2GB | PyTorch, Transformers, Phi-3 |
| `models/gemma/requirements.txt` | Gemma 7B model service | ~2.1GB | JAX, Flax, Gemma, Transformers |
| `models/mistral/requirements.txt` | Mistral 7B model service | ~1.8GB | PyTorch, Mistral-Common, BitsAndBytes |

**Total Production Size**: ~5.3GB  
**Total with Development**: ~5.4GB

### 🎯 Installation Strategy

Each requirements file serves a specific purpose in the build process:

```bash
# 1. Install project management tools first
pip install -r requirements.txt

# 2. Backend development (optional for Docker-only users)
cd backend && pip install -r requirements.txt

# 3. Development tools (for contributors only)
pip install -r requirements-dev.txt

# 4. Model services handled by Docker automatically
docker-compose build  # Installs model-specific requirements
```
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   User Service  │
│   (React/TS)    │◄───┤   (FastAPI)     │◄───┤   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  Document Gen   │ │  Job Matching   │ │  Application    │
    │  (Phi-3 Mini)   │ │  (Gemma 7B)     │ │  (Mistral 7B)   │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   Database      │
                    └─────────────────┘
```

## 📋 Prerequisites

### System Requirements
- **MacBook Air M4** (8GB+ RAM recommended)
- **Docker Desktop** (latest version)
- **Python 3.12.9**
- **Node.js 18+** and **npm/yarn**
- **Git**

### Resource Considerations
- **Available RAM**: 6GB+ free (models run sequentially)
- **Storage**: 15GB+ free space for models and data
- **Network**: Stable internet for job scraping

## 📦 Requirements Structure

This project uses **multiple requirements files** for different components to optimize Docker builds and manage dependencies efficiently:

### **Root Level** (`requirements.txt`)
- Project setup scripts (`scripts/`)
- System management tools
- Database operations
- Health checks and monitoring

### **Backend API** (`backend/requirements.txt`) 
- FastAPI web framework
- Database ORM (SQLAlchemy)
- Authentication and security
- Web scraping tools
- Application logic dependencies

### **Model Services** (separate requirements for each)
- `models/phi3/requirements.txt` - Phi-3 Mini dependencies
- `models/gemma/requirements.txt` - Gemma 7B dependencies  
- `models/mistral/requirements.txt` - Mistral 7B dependencies

### **Frontend** (`frontend/package.json`)
- React and TypeScript
- UI components and styling
- Build tools and bundlers

### **Why Multiple Requirements Files?**

#### **🎯 Benefits:**
- **Optimized Docker Images**: Each service only includes necessary dependencies
- **Faster Builds**: Docker layers cache more effectively with smaller requirement sets
- **Resource Efficiency**: Critical for MacBook Air M4's 8GB RAM limitation
- **Parallel Development**: Teams can work on different services independently
- **Security**: Reduced attack surface with minimal dependencies per service

#### **📊 Dependency Breakdown:**
```
Root (requirements.txt)          →  ~15 packages   (~50MB)
├── Backend (backend/)           →  ~45 packages   (~200MB) 
├── Phi-3 Service (models/phi3/) →  ~12 packages   (~1.2GB)
├── Gemma Service (models/gemma/) →  ~15 packages  (~2.1GB)
├── Mistral Service (models/mistral/) → ~14 packages (~1.8GB)
└── Development (requirements-dev.txt) → ~25 packages (~100MB)

Total Production: ~5.3GB
Total with Dev: ~5.4GB
```

#### **🔄 Docker Multi-Stage Builds:**
Each model service uses multi-stage builds to minimize final image size:
- **Stage 1**: Install build dependencies and compile
- **Stage 2**: Copy only runtime files and models
- **Result**: 40-60% smaller final images

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/job-automation-system.git
cd job-automation-system
```

### 2. Environment Setup

```bash
# Copy environment file
cp .env.example .env

# Edit environment variables
nano .env
```

### 3. Install Project Dependencies

```bash
# Install root-level dependencies (for setup scripts)
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Docker Setup

```bash
# Build all services (this will install service-specific dependencies)
docker-compose build

# Download LLM models (this will take time - ~10-15GB total)
python scripts/setup_models.py

# Start the application
docker-compose up -d
```

### 4. Database Migration

```bash
# Run database migrations
docker-compose exec api python -m alembic upgrade head

# Create initial admin user (optional)
docker-compose exec api python scripts/create_admin.py
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin

## 📁 Project Structure

```
job-automation-system/
├── 📁 frontend/                    # React TypeScript frontend
│   ├── 📁 src/
│   │   ├── 📁 components/         # Reusable UI components
│   │   ├── 📁 pages/             # Application pages
│   │   ├── 📁 hooks/             # Custom React hooks
│   │   ├── 📁 services/          # API service calls
│   │   ├── 📁 types/             # TypeScript type definitions
│   │   └── 📁 utils/             # Utility functions
│   ├── 📄 package.json           # Frontend dependencies
│   ├── 📄 tsconfig.json
│   └── 📄 Dockerfile
├── 📁 backend/                     # Python FastAPI backend
│   ├── 📁 app/
│   │   ├── 📁 api/               # API route handlers
│   │   │   ├── 📁 v1/
│   │   │   │   ├── 📄 auth.py    # Authentication endpoints
│   │   │   │   ├── 📄 users.py   # User management
│   │   │   │   ├── 📄 jobs.py    # Job-related endpoints
│   │   │   │   ├── 📄 documents.py # Resume/cover letter generation
│   │   │   │   └── 📄 applications.py # Application management
│   │   │   └── 📄 __init__.py
│   │   ├── 📁 core/              # Core functionality
│   │   │   ├── 📄 config.py      # Application configuration
│   │   │   ├── 📄 security.py    # Security utilities
│   │   │   ├── 📄 database.py    # Database connection
│   │   │   └── 📄 logging.py     # Logging configuration
│   │   ├── 📁 models/            # Database models
│   │   │   ├── 📄 user.py        # User model
│   │   │   ├── 📄 job.py         # Job model
│   │   │   ├── 📄 application.py # Application model with history tracking
│   │   │   ├── 📄 document.py    # Document model
│   │   │   └── 📄 application_history.py # Application history and duplicates
│   │   ├── 📁 schemas/           # Pydantic schemas
│   │   │   ├── 📄 user.py        # User schemas
│   │   │   ├── 📄 job.py         # Job schemas
│   │   │   └── 📄 document.py    # Document schemas
│   │   ├── 📁 services/          # Business logic services
│   │   │   ├── 📁 llm/           # LLM service integrations
│   │   │   │   ├── 📄 phi3_service.py      # Phi-3 Mini service
│   │   │   │   ├── 📄 gemma_service.py     # Gemma 7B service
│   │   │   │   ├── 📄 mistral_service.py   # Mistral 7B service
│   │   │   │   └── 📄 model_manager.py     # Model lifecycle management
│   │   │   ├── 📁 scrapers/      # Web scraping modules
│   │   │   │   ├── 📄 base_scraper.py      # Base scraper class
│   │   │   │   ├── 📄 linkedin_scraper.py  # LinkedIn Jobs scraper
│   │   │   │   ├── 📄 indeed_scraper.py    # Indeed scraper
│   │   │   │   ├── 📄 custom_scraper.py    # Custom portal scraper
│   │   │   │   └── 📄 scraper_factory.py   # Scraper factory
│   │   │   ├── 📄 document_service.py      # Document generation
│   │   │   ├── 📄 job_service.py           # Job matching and parsing
│   │   │   ├── 📄 application_service.py   # Application automation
│   │   │   ├── 📄 application_manager.py   # Application history and duplicate prevention
│   │   │   └── 📄 notification_service.py  # Notifications
│   │   ├── 📁 utils/             # Utility functions
│   │   │   ├── 📄 text_processing.py       # Text processing utilities
│   │   │   ├── 📄 file_handling.py         # File operations
│   │   │   ├── 📄 validation.py            # Input validation
│   │   │   └── 📄 encryption.py            # Data encryption
│   │   ├── 📁 templates/         # Document templates
│   │   │   ├── 📄 resume_template.py       # Resume templates
│   │   │   └── 📄 cover_letter_template.py # Cover letter templates
│   │   └── 📄 main.py            # FastAPI application entry
│   ├── 📁 alembic/               # Database migrations
│   ├── 📁 tests/                 # Test suite
│   │   ├── 📁 unit/              # Unit tests
│   │   ├── 📁 integration/       # Integration tests
│   │   └── 📄 conftest.py        # Test configuration
│   ├── 📄 requirements.txt       # Backend Python dependencies
│   ├── 📄 pyproject.toml         # Python project configuration
│   └── 📄 Dockerfile             # Backend Docker configuration
├── 📁 models/                      # LLM model containers
│   ├── 📁 phi3/
│   │   ├── 📄 Dockerfile          # Phi-3 Mini container
│   │   ├── 📄 model_server.py     # Model serving script
│   │   └── 📄 requirements.txt    # Phi-3 specific dependencies
│   ├── 📁 gemma/
│   │   ├── 📄 Dockerfile          # Gemma 7B container
│   │   ├── 📄 model_server.py
│   │   └── 📄 requirements.txt    # Gemma 7B specific dependencies
│   └── 📁 mistral/
│       ├── 📄 Dockerfile          # Mistral 7B container
│       ├── 📄 model_server.py
│       └── 📄 requirements.txt    # Mistral 7B specific dependencies
├── 📁 nginx/                       # Reverse proxy configuration
│   ├── 📄 nginx.conf
│   └── 📄 Dockerfile
├── 📁 scripts/                     # Utility scripts
│   ├── 📄 setup_models.py         # Model download and setup
│   ├── 📄 create_admin.py         # Admin user creation
│   ├── 📄 backup_db.py            # Database backup
│   └── 📄 health_check.py         # System health check
├── 📁 config/                      # Configuration files
│   └── 📄 portals.yml             # Custom job portals configuration
├── 📁 docs/                        # Documentation
│   ├── 📄 api.md                  # API documentation
│   ├── 📄 deployment.md           # Deployment guide
│   └── 📄 architecture.md         # Architecture overview
├── 📄 docker-compose.yml          # Docker Compose configuration
├── 📄 docker-compose.prod.yml     # Production configuration
├── 📄 requirements.txt            # Root project dependencies (scripts & tools)
├── 📄 requirements-dev.txt        # Development dependencies
├── 📄 .env.example                # Environment variables template
├── 📄 .gitignore                  # Git ignore rules
├── 📄 README.md                   # This file
└── 📄 LICENSE                     # License information
```

## 💻 Usage

### 1. User Registration and Profile Setup

1. **Register**: Create an account at http://localhost:3000/register
2. **Profile Setup**: Complete your professional profile including:
   - Personal information
   - Work experience
   - Skills and certifications
   - Education background
   - Job preferences (salary, location, etc.)

### 2. Adding Custom Job Portals

1. Navigate to **Profile > Job Portals**
2. Click **"Add Portal"**
3. Enter portal details:
   ```
   Portal Name: TechCorp Careers
   URL: https://techcorp.com/careers
   Portal Type: Company Website
   ```
4. Configure scraping settings (optional)

### 3. Job Search and Matching

1. Go to **Jobs > Search**
2. Set search criteria:
   - Keywords
   - Location
   - Salary range
   - Job type
3. Click **"Find Jobs"** - Gemma 7B will analyze and score matches

### 4. Document Generation

1. Select a job from search results
2. Click **"Generate Documents"**
3. Phi-3 Mini will create:
   - Tailored resume
   - Personalized cover letter
4. Review and edit documents if needed

### 5. Automated Application

1. Review generated documents
2. Click **"Apply Now"**
3. Mistral 7B will:
   - Check against application history to prevent duplicates
   - Fill application forms
   - Submit applications
   - Save job details and application status
   - Track application status

### 6. Application Management

1. Go to **Applications > History**
2. View all previous applications:
   - Job title and company
   - Application date and status
   - Job description and requirements
   - Direct links to job postings
   - Generated documents used
3. Filter and search through application history
4. Update application status manually if needed
5. View duplicate prevention logs

## 📋 Application Manager

The Application Manager is a comprehensive system that tracks all job applications and prevents duplicate submissions.

### Key Features

#### 🔍 Duplicate Detection
- **URL Matching**: Automatically detects identical job posting URLs
- **Content Analysis**: Uses AI to identify similar job descriptions from different portals
- **Company-Position Matching**: Prevents applications to the same role at the same company
- **Smart Fuzzy Matching**: Identifies variations in job titles and descriptions

#### 📊 Application History
- **Complete Record**: Stores all application details including:
  - Job title, company, and location
  - Original job posting URL and description
  - Application date and current status
  - Generated resume and cover letter versions
  - Portal source and application method
- **Status Tracking**: Monitor application progress through various stages
- **Document Versioning**: Keep track of which documents were used for each application

#### 🚫 Prevention System
- **Pre-Application Check**: Automatically scans for duplicates before applying
- **Smart Warnings**: Alerts user if similar jobs are detected
- **Manual Override**: Option to apply anyway if user confirms it's not a duplicate
- **Whitelist Management**: Maintain exceptions for legitimate re-applications

### How It Works

#### 1. Before Each Application
```python
# System automatically checks:
1. Exact URL match in application history
2. Company name + job title similarity
3. Job description content analysis using Gemma 7B
4. Location and salary range comparison
```

#### 2. During Application Process
```python
# If potential duplicate found:
1. Display warning with similar applications
2. Show comparison of job details
3. Allow user to proceed or skip
4. Log decision for future reference
```

#### 3. After Successful Application
```python
# System saves:
1. Complete job posting data
2. Application timestamp and method
3. Generated documents (resume/cover letter)
4. Initial status and tracking information
```

### Database Structure

The Application Manager uses several database tables:

- **applications**: Main application records
- **application_history**: Detailed history and status changes
- **duplicate_checks**: Record of duplicate detection results
- **application_documents**: Links between applications and generated documents

### Technical Implementation

#### Duplicate Detection Algorithms

1. **URL-Based Matching**
   ```python
   # Normalize URLs by removing tracking parameters
   # Compare using sequence matching algorithms
   similarity = SequenceMatcher(None, url1_normalized, url2_normalized).ratio()
   ```

2. **Content Similarity Analysis**
   ```python
   # Multi-factor analysis:
   # - Job title similarity (75% threshold)
   # - Company name matching (90% threshold)  
   # - Description content analysis (85% threshold)
   # - Location proximity matching
   ```

3. **AI-Powered Semantic Detection**
   ```python
   # Uses Gemma 7B for semantic understanding
   # Analyzes job requirements and responsibilities
   # Detects role similarities across different job titles
   ```

### Frontend Features

#### Application Dashboard
- **Overview Cards**: Quick stats on total applications, response rates, recent activity
- **Status Pipeline**: Visual representation of applications in different stages
- **Recent Applications**: List of most recent job applications with quick actions
- **Upcoming Follow-ups**: Calendar view of scheduled follow-up actions

#### Application History Page
- **Advanced Filtering**: Filter by status, date range, company, job title
- **Search Functionality**: Full-text search across job titles, companies, descriptions
- **Bulk Actions**: Update multiple application statuses, add notes, schedule follow-ups
- **Export Options**: Export application data to CSV, PDF reports

#### Duplicate Prevention Interface
- **Real-time Warnings**: Immediate alerts when similar jobs are detected
- **Side-by-side Comparison**: Compare current job with potentially duplicate applications
- **Override Options**: Allow users to proceed with application if they confirm it's not a duplicate
- **Similarity Scores**: Visual indicators showing confidence levels of duplicate detection

#### Analytics and Insights
- **Application Metrics**: Success rates, time-to-response, most effective portals
- **Company Insights**: Track which companies respond most frequently
- **Trend Analysis**: Seasonal patterns, industry response rates
- **Performance Optimization**: Suggestions for improving application success rates

- **Indexed Database Queries**: Fast lookups using PostgreSQL indexes
- **Caching Layer**: Redis cache for frequently checked URLs and companies
- **Batch Processing**: Background jobs for updating application statuses
- **Rate Limiting**: Prevents excessive duplicate checks

Users can customize the duplicate detection sensitivity:

```yaml
duplicate_detection:
  url_matching: true          # Exact URL matching
  content_similarity: 0.85    # Content similarity threshold (0.0-1.0)
  title_similarity: 0.75      # Job title similarity threshold
  company_matching: true      # Company name matching
  location_tolerance: 50      # Distance tolerance in km
  time_window: 30            # Days to consider for duplicates
```

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/jobautomation
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM Configuration
PHI3_MODEL_PATH=/models/phi3-mini
GEMMA_MODEL_PATH=/models/gemma-7b
MISTRAL_MODEL_PATH=/models/mistral-7b-instruct

# Model Server URLs
PHI3_SERVICE_URL=http://phi3-service:8001
GEMMA_SERVICE_URL=http://gemma-service:8002
MISTRAL_SERVICE_URL=http://mistral-service:8003

# Scraping Configuration
SCRAPING_DELAY=2
MAX_CONCURRENT_REQUESTS=5
USER_AGENT=JobAutomation/1.0

# Notification Settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Feature Flags
ENABLE_AUTO_APPLY=true
ENABLE_NOTIFICATIONS=true
ENABLE_ANALYTICS=true
ENABLE_DUPLICATE_DETECTION=true

# Application Manager Settings
DUPLICATE_SIMILARITY_THRESHOLD=0.85
APPLICATION_HISTORY_RETENTION_DAYS=365
ENABLE_APPLICATION_ANALYTICS=true
AUTO_STATUS_UPDATES=true
```

### Custom Portal Configuration

Add custom job portals via the web interface or configuration file:

```yaml
# config/portals.yml
portals:
  - name: "Google Careers"
    url: "https://careers.google.com/jobs/results/"
    type: "company"
    selectors:
      job_title: ".gc-card__title"
      job_link: ".gc-card__title a"
      location: ".gc-card__location"
    rate_limit: 1  # requests per second

  - name: "GitHub Jobs"
    url: "https://jobs.github.com/positions"
    type: "job_board"
    api_endpoint: "https://jobs.github.com/positions.json"
    requires_auth: false
```

## 📚 API Documentation

### Authentication Endpoints

```python
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

### User Management

```python
GET /api/v1/users/profile
PUT /api/v1/users/profile
POST /api/v1/users/portals
DELETE /api/v1/users/portals/{portal_id}
```

### Job Operations

```python
GET /api/v1/jobs/search
POST /api/v1/jobs/analyze
GET /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/apply
```

### Document Generation

```python
POST /api/v1/documents/resume
POST /api/v1/documents/cover-letter
GET /api/v1/documents/{document_id}
PUT /api/v1/documents/{document_id}
```

### Application Tracking

```python
GET /api/v1/applications
GET /api/v1/applications/{application_id}
PUT /api/v1/applications/{application_id}/status
GET /api/v1/applications/history
POST /api/v1/applications/check-duplicate
GET /api/v1/applications/statistics
DELETE /api/v1/applications/{application_id}
```

### Application Manager

```python
GET /api/v1/applications/manager/history
POST /api/v1/applications/manager/check-duplicate
GET /api/v1/applications/manager/duplicates
PUT /api/v1/applications/manager/merge-duplicates
GET /api/v1/applications/manager/analytics
```

## 🧪 Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/job-automation-system.git
cd job-automation-system

# Install project management tools
pip install -r requirements.txt

# Backend development
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r ../requirements-dev.txt

# Frontend development
cd ../frontend
npm install
npm start

# Start supporting services only (for local development)
docker-compose up -d db redis

# Or start everything with Docker
docker-compose -f docker-compose.dev.yml up
```

### Working with Requirements

#### **Adding New Dependencies**
```bash
# For backend API features
echo "new-package==1.0.0" >> backend/requirements.txt

# For project scripts
echo "new-tool==2.0.0" >> requirements.txt

# For development only
echo "dev-tool==1.5.0" >> requirements-dev.txt

# Rebuild affected containers
docker-compose build api
```

#### **Updating Dependencies**
```bash
# Check outdated packages
pip list --outdated

# Update specific service requirements
cd backend && pip-compile requirements.in  # if using pip-tools
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Code Quality

```bash
# Python linting and formatting
black app/
isort app/
flake8 app/
mypy app/

# TypeScript linting
cd frontend
npm run lint
npm run type-check
```

## 🔧 Troubleshooting

### Dependency Management

#### Requirements File Issues
```bash
# If you encounter dependency conflicts, try installing in isolation:

# For project scripts only
pip install -r requirements.txt

# For backend development
cd backend && pip install -r requirements.txt

# For development tools
pip install -r requirements-dev.txt
```

#### Docker Build Issues
```bash
# Clean build if dependencies fail
docker-compose down
docker system prune -f
docker-compose build --no-cache

# Build individual services
docker-compose build api
docker-compose build phi3-service
```

#### Model Service Dependencies
```bash
# If model services fail to start, check logs:
docker-compose logs phi3-service
docker-compose logs gemma-service
docker-compose logs mistral-service

# Restart specific model service
docker-compose restart phi3-service
```

### Common Issues

#### Model Loading Issues
```bash
# Check model availability
docker-compose exec phi3-service python -c "from transformers import AutoModel; print('Phi-3 loaded successfully')"

# Restart model services
docker-compose restart phi3-service gemma-service mistral-service
```

#### Database Connection Issues
```bash
# Check database status
docker-compose exec db psql -U postgres -c "SELECT version();"

# Reset database
docker-compose down -v
docker-compose up -d db
docker-compose exec api python -m alembic upgrade head
```

#### Memory Issues on MacBook Air M4
```bash
# Monitor resource usage
docker stats

# Optimize memory usage
export DOCKER_DEFAULT_PLATFORM=linux/arm64
docker-compose -f docker-compose.yml -f docker-compose.memory-optimized.yml up
```

#### Application Manager Issues
```bash
# Check application history
docker-compose exec api python -c "from app.services.application_manager import ApplicationManager; am = ApplicationManager(); print(am.get_stats())"

# Clear duplicate detection cache
docker-compose exec api python scripts/clear_duplicate_cache.py

# Rebuild application index
docker-compose exec api python scripts/rebuild_application_index.py

# Check for orphaned applications
docker-compose exec api python scripts/check_application_integrity.py
```

```bash
# View application logs
docker-compose logs -f api

# Debug specific service
docker-compose exec api python -c "from app.services.llm.phi3_service import test_connection; test_connection()"

# Database logs
docker-compose logs db
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with proper type hints and docstrings
4. Add tests for new functionality
5. Run the test suite: `pytest`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Code Standards

- **Python**: Follow PEP 8, use type hints, write Sphinx-style docstrings
- **TypeScript**: Follow ESLint rules, use strict typing
- **Documentation**: Update docs for any new features
- **Testing**: Maintain >90% test coverage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LLM Models**: Thanks to Microsoft (Phi-3), Google (Gemma), and Mistral AI
- **Community**: Built with love for the job-seeking community
- **Open Source**: Powered by amazing open-source libraries

## 📞 Support

- **Documentation**: [Project Wiki](https://github.com/yourusername/job-automation-system/wiki)
- **Issues**: [GitHub Issues](https://github.com/yourusername/job-automation-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/job-automation-system/discussions)

---

**Happy Job Hunting! 🎯**

*Built with ❤️ for automating the job application process*