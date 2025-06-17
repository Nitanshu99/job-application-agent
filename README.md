# 🚀 AI-Powered Job Application Automation System

> **Transform your job search with AI** - Apply to hundreds of jobs in minutes, not hours!

[![Python Version](https://img.shields.io/badge/python-3.12.9-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MacBook M4](https://img.shields.io/badge/optimized%20for-MacBook%20M4-orange.svg)](https://www.apple.com/macbook-air/)

## 📖 Table of Contents

- [What is This?](#-what-is-this)
- [How It Works](#-how-it-works)
- [System Architecture](#-system-architecture)
- [Prerequisites](#-prerequisites)
- [Installation Guide](#-installation-guide)
- [Project Structure Explained](#-project-structure-explained)
- [How to Use](#-how-to-use)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Contributing](#-contributing)

## 🎯 What is This?

This is an **AI-powered system** that automates the entire job application process. Instead of spending hours customizing resumes and filling out applications, our system does it all for you using cutting-edge AI models.

### 🌟 Key Features

- **🤖 Smart Job Matching**: AI analyzes jobs and ranks them by compatibility with your profile
- **📝 Custom Documents**: Generates tailored resumes and cover letters for each job
- **🚀 Auto-Apply**: Fills and submits job applications automatically
- **🚫 Duplicate Prevention**: Never apply to the same job twice
- **📊 Application Tracking**: Monitor all your applications in one place
- **🔔 Smart Notifications**: Get alerts for new matches and application updates

### 💡 Perfect For

- **Job Seekers**: Apply to more jobs in less time
- **Career Changers**: Highlight transferable skills for new roles
- **Recent Graduates**: Stand out with AI-optimized applications
- **Busy Professionals**: Automate the tedious parts of job hunting

## 🔄 How It Works

### System Architecture

![System Architecture](architecture-diagram.svg)

*Our system uses a microservices architecture with three specialized AI models working together*

### Data Flow & User Journey

![Data Flow](data-flow-diagram.svg)

*See how your data flows through the system and the complete user journey from registration to job offers*

## 💻 Prerequisites

### For Everyone (Required)

1. **MacBook M4** (or any Mac with Apple Silicon)
   - At least 16GB RAM
   - 20GB free storage space

2. **Software to Install**
   - [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
   - [Python 3.12.9](https://www.python.org/downloads/)
   - [Node.js 18+](https://nodejs.org/)
   - [Git](https://git-scm.com/)

### Quick Check Commands

Open Terminal and run these commands to verify:

```bash
# Check Python
python3 --version  # Should show 3.12.9

# Check Docker
docker --version   # Should show Docker version

# Check Node.js
node --version     # Should show v18 or higher

# Check Git
git --version      # Should show git version
```

## 🛠️ Installation Guide

### Step 1: Download the Project

```bash
# Clone the repository
git clone https://github.com/yourusername/job-automation-system.git

# Enter the project folder
cd job-automation-system
```

### Step 2: Set Up Environment

```bash
# Copy the example environment file
cp .env.example .env

# Open .env in a text editor and add your details
nano .env
```

**Important .env settings:**
```env
# Database (keep defaults for local development)
DATABASE_URL=postgresql://postgres:postgres@db:5432/jobautomation

# Security (generate a random secret)
SECRET_KEY=your-super-secret-key-here

# Email (for notifications)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Step 3: Run the Magic Script 🪄

We've created a simple script that handles everything:

```bash
# Make the script executable
chmod +x project_manager.sh

# Install everything
./project_manager.sh install

# Start the application
./project_manager.sh run
```

### Step 4: Access the Application

Once running, open your browser and go to:
- **Main App**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

## 📁 Project Structure Explained

### 🏠 Root Directory Files

| File | What It Does | For Whom |
|------|--------------|----------|
| `project_manager.sh` | One-click setup and run script | Everyone - Your best friend! |
| `docker-compose.yml` | Configures all services | Advanced users |
| `docker-compose.prod.yml` | Production settings | Deployment only |
| `.env.example` | Template for environment variables | Everyone - Copy this! |
| `requirements.txt` | Python packages for scripts | Python developers |
| `requirements-dev.txt` | Development tools | Contributors only |
| `.gitignore` | Files Git should ignore | Developers |
| `README.md` | This file you're reading! | Everyone |

### 📂 Frontend (`/frontend`)

The user interface built with React and TypeScript.

| Path | Purpose | Key Files |
|------|---------|-----------|
| `/src/components` | Reusable UI components | `JobCard.tsx`, `ApplicationForm.tsx` |
| `/src/pages` | Main app pages | `Dashboard.tsx`, `JobSearch.tsx` |
| `/src/services` | API communication | `api.ts`, `auth.ts` |
| `/src/hooks` | Custom React hooks | `useJobs.ts`, `useApplications.ts` |
| `package.json` | Frontend dependencies | Lists all npm packages |
| `Dockerfile` | Container configuration | For Docker deployment |

### 📂 Backend (`/backend`)

The API server built with FastAPI (Python).

| Path | Purpose | Key Files |
|------|---------|-----------|
| `/app/api/v1` | API endpoints | `auth.py`, `jobs.py`, `applications.py` |
| `/app/core` | Core functionality | `config.py`, `security.py`, `database.py` |
| `/app/models` | Database models | `user.py`, `job.py`, `application.py` |
| `/app/schemas` | Data validation | Request/response formats |
| `/app/services` | Business logic | `application_service.py`, `job_scraper.py` |
| `/app/templates` | Document templates | `resume_template.py` |
| `requirements.txt` | Python packages | All backend dependencies |

### 📂 AI Models (`/models`)

Three specialized AI models, each in its own folder:

#### `/models/phi3` - Document Generator
- `model_server.py`: Serves the Phi-3 model
- `requirements.txt`: Model-specific packages
- `Dockerfile`: Container setup
- **Purpose**: Creates tailored resumes and cover letters

#### `/models/gemma` - Job Matcher
- `model_server.py`: Serves the Gemma 7B model
- `requirements.txt`: Model-specific packages
- `Dockerfile`: Container setup
- **Purpose**: Analyzes and scores job compatibility

#### `/models/mistral` - Application Filler
- `model_server.py`: Serves the Mistral 7B model
- `requirements.txt`: Model-specific packages
- `Dockerfile`: Container setup
- **Purpose**: Fills out job application forms

### 📂 Infrastructure (`/nginx`)

- `nginx.conf`: Reverse proxy configuration
- `Dockerfile`: Nginx container setup
- **Purpose**: Routes traffic between frontend and backend

### 📂 Scripts (`/scripts`)

Utility scripts for various tasks:

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `setup_models.py` | Downloads AI models | First-time setup |
| `create_admin.py` | Creates admin user | Optional |
| `backup_db.py` | Backs up database | Regular maintenance |
| `health_check.py` | Checks system status | Troubleshooting |

### 📂 Configuration (`/config`)

- `portals.yml`: Job portal configurations
- Add your favorite job sites here!

## 🚀 How to Use

### 🎬 First Time Setup (10 minutes)

1. **Create Your Account**
   ```
   1. Go to http://localhost:3000
   2. Click "Sign Up"
   3. Enter your email and password
   4. Verify your email
   ```

2. **Build Your Profile**
   ```
   Navigate to Profile → Edit Profile
   
   Fill in:
   ✓ Personal Info (name, location, phone)
   ✓ Work Experience (add all past jobs)
   ✓ Education (degrees, certifications)
   ✓ Skills (be comprehensive!)
   ✓ Preferences (salary, location, remote)
   ```

3. **Add Job Portals**
   ```
   Go to Settings → Job Portals
   
   Add sites like:
   - https://www.linkedin.com/jobs
   - https://careers.google.com
   - https://jobs.microsoft.com
   - Your favorite job boards
   ```

### 📅 Daily Usage (5 minutes)

1. **Check New Matches**
   ```
   Dashboard shows:
   🔵 12 new job matches
   🟢 8 applications in review
   🟡 3 interviews scheduled
   ```

2. **Apply to Jobs**
   ```
   1. Click on a job match
   2. Review AI-generated score (e.g., 92% match)
   3. Click "Generate Documents"
   4. Review resume and cover letter
   5. Click "Apply Now"
   ```

3. **Track Progress**
   ```
   Applications tab shows:
   - Applied jobs with status
   - Response rates
   - Upcoming interviews
   ```

## ⚙️ Configuration

### Basic Settings (`.env` file)

```env
# App Settings
APP_NAME="Job Automation System"
DEBUG=false  # Set to true for development

# Model Settings (adjust based on your RAM)
PHI3_MAX_MEMORY=4G     # Document generation
GEMMA_MAX_MEMORY=6G    # Job matching
MISTRAL_MAX_MEMORY=4G  # Application filling

# Job Search Defaults
DEFAULT_SEARCH_RADIUS=50  # miles
MAX_APPLICATIONS_PER_DAY=20
```

### Advanced Configuration

#### Custom Job Portals (`/config/portals.yml`)
```yaml
portals:
  - name: "Tech Jobs"
    url: "https://techjobs.com"
    selectors:
      job_title: ".job-title"
      company: ".company-name"
      description: ".job-description"
```

#### Model Optimization
```python
# In model_server.py files
MODEL_CONFIG = {
    "max_length": 2048,      # Reduce for faster processing
    "temperature": 0.7,      # Increase for more creative outputs
    "batch_size": 1,         # Keep at 1 for M4 Macs
}
```

## 🔧 Troubleshooting

### Common Issues

#### 1. "Docker not running"
```bash
# Solution: Start Docker Desktop
open -a Docker

# Wait for Docker to start, then retry
./project_manager.sh run
```

#### 2. "Out of memory"
```bash
# Solution: Increase Docker memory
1. Open Docker Desktop
2. Go to Settings → Resources
3. Set Memory to at least 10GB
4. Click "Apply & Restart"
```

#### 3. "Models not loading"
```bash
# Solution: Re-download models
cd models
python setup_models.py --force
```

#### 4. "Application stuck"
```bash
# Solution: Check specific service logs
docker-compose logs phi3-service    # For document generation issues
docker-compose logs gemma-service   # For job matching issues
docker-compose logs mistral-service # For application issues
```

### 🚨 Emergency Commands

```bash
# Stop everything
./project_manager.sh stop

# Complete reset
docker-compose down -v
rm -rf models/*/model_files/
./project_manager.sh install

# Check system status
./project_manager.sh status
```

## ❓ FAQ

### For Job Seekers

**Q: Is this legal?**
A: Yes! You're simply automating the process of filling out public job applications with your real information.

**Q: Will employers know I used AI?**
A: The system generates human-like, personalized content. However, always review before submitting.

**Q: How many jobs can I apply to?**
A: The system can handle 50-100 applications per day, but we recommend quality over quantity.

### For Developers

**Q: Can I add my own job sites?**
A: Yes! Add them to `/config/portals.yml` with the appropriate selectors.

**Q: How do I modify the AI prompts?**
A: Check the `*_service.py` files in each model directory.

**Q: Can this run on other systems?**
A: With modifications, yes. It's optimized for MacBook M4 but can work on other systems with adequate RAM.

### Technical

**Q: Why three separate AI models?**
A: Each model is specialized for its task, providing better results than one general model.

**Q: How is my data protected?**
A: All data is stored locally, passwords are encrypted, and API uses JWT authentication.

**Q: Can I use cloud storage?**
A: Yes, the system supports S3 for document storage. Configure in `.env`.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **AI Models**: Microsoft (Phi-3), Google (Gemma), Mistral AI
- **Community**: Built for job seekers everywhere
- **Contributors**: See [CONTRIBUTORS.md](CONTRIBUTORS.md)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/job-automation-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/job-automation-system/discussions)
- **Email**: support@jobautomation.ai

---

**Happy Job Hunting! 🎯**

*Remember: This tool is meant to help you apply to more jobs efficiently, but always personalize and review before submitting!*