#!/bin/bash

# Project Manager Script for Resume App
# Usage: ./project_manager.sh [install|run|stop]

set -e  # Exit on any error

# Configuration
CONDA_ENV="resume-app"
PROJECT_NAME="resume-app"
PID_FILE="./app.pid"
LOG_FILE="./app.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to activate conda environment
activate_conda_env() {
    print_status "Activating conda environment: $CONDA_ENV"
    
    # Initialize conda for bash
    if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif command -v conda &> /dev/null; then
        eval "$(conda shell.bash hook)"
    else
        print_error "Conda not found. Please install conda or update the script with correct conda path."
        exit 1
    fi
    
    # Check if environment exists
    if conda env list | grep -q "^$CONDA_ENV "; then
        conda activate $CONDA_ENV
        print_success "Conda environment '$CONDA_ENV' activated"
    else
        print_error "Conda environment '$CONDA_ENV' not found"
        print_status "Available environments:"
        conda env list
        exit 1
    fi
}

# Function to install and setup project
install_project() {
    print_status "Starting project installation and setup..."
    
    # Activate conda environment
    activate_conda_env
    
    # Update pip (skip conda update as it's global)
    print_status "Updating pip..."
    pip install --upgrade pip
    
    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        print_status "Installing root project dependencies from requirements.txt..."
        pip install -r requirements.txt
    fi
    
    # Install backend dependencies
    if [ -d "backend" ] && [ -f "backend/requirements.txt" ]; then
        print_status "Installing backend dependencies..."
        
        # Try installing with exact versions first
        if pip install -r backend/requirements.txt 2>/dev/null; then
            print_success "Backend dependencies installed successfully"
        else
            print_warning "Some dependencies failed with exact versions. Trying flexible installation..."
            
            # Try installing without strict version constraints (macOS compatible)
            print_status "Attempting to resolve dependency conflicts..."
            
            # Create a temporary requirements file without strict pins using python
            python3 -c "
import re
with open('backend/requirements.txt', 'r') as f:
    content = f.read()
    
# Replace == with >= for flexible versions
flexible_content = re.sub(r'==', '>=', content)

with open('temp_requirements.txt', 'w') as f:
    f.write(flexible_content)
"
            
            if pip install -r temp_requirements.txt; then
                print_success "Backend dependencies installed with flexible versions"
                print_warning "Some package versions may differ from requirements.txt"
            else
                print_error "Failed to install backend dependencies"
                print_status "Please check backend/requirements.txt for version conflicts"
                rm -f temp_requirements.txt
                return 1
            fi
            
            rm -f temp_requirements.txt
        fi
        
        # Ensure uvicorn is installed for FastAPI
        pip install "uvicorn[standard]>=0.20.0" 2>/dev/null || pip install uvicorn
    fi
    
    # Install development dependencies (optional)
    if [ -f "requirements-dev.txt" ]; then
        print_status "Installing development dependencies (optional)..."
        pip install -r requirements-dev.txt 2>/dev/null || print_warning "Could not install dev dependencies"
    fi
    
    # Install Node.js dependencies for frontend
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        print_status "Installing frontend dependencies..."
        cd frontend
        if command -v npm &> /dev/null; then
            npm install
        elif command -v yarn &> /dev/null; then
            yarn install
        else
            print_warning "No Node.js package manager found. Skipping frontend dependencies."
        fi
        cd ..
    elif [ -f "package.json" ]; then
        print_status "Installing Node.js dependencies..."
        if command -v npm &> /dev/null; then
            npm install
        elif command -v yarn &> /dev/null; then
            yarn install
        else
            print_warning "No Node.js package manager found. Skipping Node.js dependencies."
        fi
    fi
    
    # Setup database if needed
    if [ -f "database/init.sql" ]; then
        print_status "Setting up database..."
        # Add your database setup commands here
        # Example: python manage.py migrate
    fi
    
    # Create necessary directories
    print_status "Creating necessary directories..."
    mkdir -p logs
    mkdir -p uploads
    mkdir -p static
    mkdir -p media
    
    # Setup environment variables template
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please update the .env file with your configuration"
    fi
    
    # Run model setup if available (for job automation system)
    if [ -f "scripts/setup_models.py" ]; then
        print_status "Setting up LLM models (this may take time - ~10-15GB)..."
        python scripts/setup_models.py || print_warning "Model setup failed - you can run this manually later"
    fi
    
    # Run any additional setup scripts
    if [ -f "setup.py" ]; then
        print_status "Running setup.py..."
        python setup.py develop
    fi
    
    # Build frontend if needed
    if [ -f "package.json" ] && [ -f "webpack.config.js" ]; then
        print_status "Building frontend assets..."
        npm run build 2>/dev/null || yarn build 2>/dev/null || print_warning "No build script found"
    fi
    
    print_success "Job automation system installation completed successfully!"
    print_status ""
    print_status "🎯 Next steps:"
    print_status "1. Update .env file with your configuration"
    print_status "2. Start the system: $0 run"
    print_status "3. Access the API docs: http://localhost:8000/docs"
    print_status "4. Access the frontend: http://localhost:3000"
    print_status ""
    print_status "🔧 Optional Docker services:"
    print_status "   docker-compose up -d db redis  # Database and cache"
}

# Function to run the project
run_project() {
    print_status "Starting the project..."
    
    # Activate conda environment
    activate_conda_env
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        print_warning "Project may already be running. Check with: $0 status"
        print_status "Use '$0 stop' to stop the project first if needed"
        # Don't exit, allow restart
    fi
    
    # Start the application
    print_status "Starting job automation system..."
    
    # Check for supporting services
    print_status "Checking for supporting services (database, redis)..."
    if command -v docker-compose &> /dev/null; then
        print_status "Starting supporting services with Docker..."
        docker-compose up -d db redis 2>/dev/null || print_warning "Could not start supporting services"
    fi
    
    # Start FastAPI backend
    if [ -d "backend" ] && [ -f "backend/app/main.py" ]; then
        # Check if uvicorn is available
        if ! command -v uvicorn &> /dev/null; then
            print_error "uvicorn not found. Installing..."
            pip install uvicorn[standard]
        fi
        
        print_status "Starting FastAPI backend server..."
        cd backend
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../$LOG_FILE 2>&1 &
        BACKEND_PID=$!
        cd ..
        
        # Save backend PID
        echo "BACKEND:$BACKEND_PID" > $PID_FILE
        
        # Wait and check if backend started
        sleep 3
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            print_success "Backend started successfully (PID: $BACKEND_PID)"
            print_status "API Documentation: http://localhost:8000/docs"
        else
            print_error "Failed to start backend"
            rm -f $PID_FILE
            exit 1
        fi
    fi
    
    # Start React frontend if available
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        print_status "Starting React frontend..."
        cd frontend
        
        # Check if npm start script exists
        if npm run --silent 2>/dev/null | grep -q "start"; then
            npm start > ../frontend.log 2>&1 &
        else
            # Try alternative commands
            npm run dev > ../frontend.log 2>&1 &
        fi
        
        FRONTEND_PID=$!
        cd ..
        
        # Append frontend PID
        echo "FRONTEND:$FRONTEND_PID" >> $PID_FILE
        
        # Wait and check if frontend started
        sleep 5
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            print_success "Frontend started successfully (PID: $FRONTEND_PID)"
            print_status "Frontend URL: http://localhost:3000"
        else
            print_warning "Frontend failed to start (check frontend.log)"
        fi
    fi
    
    # If no backend/frontend, try CLI mode
    if [ ! -d "backend" ] && [ ! -d "frontend" ]; then
        if [ -f "main.py" ]; then
            print_status "Starting CLI application..."
            python main.py > $LOG_FILE 2>&1 &
            APP_PID=$!
            echo "CLI:$APP_PID" > $PID_FILE
        else
            print_error "No recognizable application entry point found"
            print_status "Expected: backend/app/main.py, frontend/package.json, or main.py"
            exit 1
        fi
    fi
    
    print_success "Job automation system started successfully!"
    print_status "Backend API: http://localhost:8000/docs"
    print_status "Frontend UI: http://localhost:3000 (if available)"
    print_status "Logs: tail -f $LOG_FILE"
    print_status "Frontend logs: tail -f frontend.log"
    print_status "Stop with: $0 stop"
}

# Function to stop the project
stop_project() {
    print_status "Stopping the project..."
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "No PID file found. Project may not be running."
        return
    fi
    
    # Read all PIDs from file
    while IFS= read -r line; do
        if [[ $line == *":"* ]]; then
            # New format: SERVICE:PID
            SERVICE=$(echo $line | cut -d':' -f1)
            PID=$(echo $line | cut -d':' -f2)
        else
            # Old format: just PID
            SERVICE="APP"
            PID=$line
        fi
        
        if ps -p $PID > /dev/null 2>&1; then
            print_status "Stopping $SERVICE (PID: $PID)..."
            
            # Try graceful shutdown first
            kill -TERM $PID
            
            # Wait up to 10 seconds for graceful shutdown
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                print_warning "Graceful shutdown failed for $SERVICE. Force killing..."
                kill -KILL $PID
            fi
            
            print_success "$SERVICE stopped successfully"
        else
            print_warning "$SERVICE with PID $PID is not running"
        fi
    done < "$PID_FILE"
    
    # Cleanup
    rm -f $PID_FILE
    rm -f frontend.log
    
    # Stop Docker services if they were started
    if command -v docker-compose &> /dev/null; then
        print_status "Stopping supporting Docker services..."
        docker-compose stop db redis 2>/dev/null || true
    fi
    
    # Kill any remaining processes on common ports (optional)
    print_status "Cleaning up any remaining processes on common ports..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true  # Backend
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true  # Frontend
    
    print_status "Resources freed and cleanup completed"
}

# Function to check project status
status_project() {
    print_status "Checking project status..."
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "No PID file found. Project is not running."
        return
    fi
    
    # Check each service
    while IFS= read -r line; do
        if [[ $line == *":"* ]]; then
            SERVICE=$(echo $line | cut -d':' -f1)
            PID=$(echo $line | cut -d':' -f2)
        else
            SERVICE="APP"
            PID=$line
        fi
        
        if ps -p $PID > /dev/null 2>&1; then
            print_success "$SERVICE is running (PID: $PID)"
        else
            print_error "$SERVICE is not running (PID: $PID)"
        fi
    done < "$PID_FILE"
    
    # Check ports
    print_status ""
    print_status "Port status:"
    if lsof -Pi :8000 -sTCP:LISTEN > /dev/null 2>&1; then
        print_success "Backend API (port 8000): Running"
    else
        print_warning "Backend API (port 8000): Not running"
    fi
    
    if lsof -Pi :3000 -sTCP:LISTEN > /dev/null 2>&1; then
        print_success "Frontend (port 3000): Running"
    else
        print_warning "Frontend (port 3000): Not running"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {install|run|stop|status}"
    echo ""
    echo "Commands:"
    echo "  install  - Set up the entire project end to end"
    echo "  run      - Start running the project"
    echo "  stop     - Stop the project and save resources"
    echo "  status   - Check if the project is running"
    echo ""
    echo "Examples:"
    echo "  $0 install"
    echo "  $0 run"
    echo "  $0 stop"
    echo "  $0 status"
}

# Main script logic
case "${1:-}" in
    install)
        install_project
        ;;
    run)
        run_project
        ;;
    stop)
        stop_project
        ;;
    status)
        status_project
        ;;
    *)
        show_usage
        exit 1
        ;;
esac