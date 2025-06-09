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
    
    # Update conda and pip
    print_status "Updating conda and pip..."
    conda update -y conda
    pip install --upgrade pip
    
    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        print_status "Installing Python dependencies from requirements.txt..."
        pip install -r requirements.txt
    fi
    
    # Install Node.js dependencies if package.json exists
    if [ -f "package.json" ]; then
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
    
    # Set up environment variables template
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please update the .env file with your configuration"
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
    
    print_success "Project installation completed successfully!"
    print_status "You can now run the project with: $0 run"
}

# Function to run the project
run_project() {
    print_status "Starting the project..."
    
    # Activate conda environment
    activate_conda_env
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "Project is already running with PID: $PID"
            print_status "Use '$0 stop' to stop the project first"
            exit 1
        else
            print_warning "Stale PID file found. Removing..."
            rm -f $PID_FILE
        fi
    fi
    
    # Start the application
    print_status "Starting application server..."
    
    # Common startup commands (uncomment/modify as needed)
    # For Flask applications:
    # python app.py > $LOG_FILE 2>&1 &
    
    # For Django applications:
    # python manage.py runserver 0.0.0.0:8000 > $LOG_FILE 2>&1 &
    
    # For FastAPI applications:
    # uvicorn main:app --host 0.0.0.0 --port 8000 > $LOG_FILE 2>&1 &
    
    # For Node.js applications:
    # node server.js > $LOG_FILE 2>&1 &
    # npm start > $LOG_FILE 2>&1 &
    
    # Generic Python application
    if [ -f "main.py" ]; then
        python main.py > $LOG_FILE 2>&1 &
        APP_PID=$!
    elif [ -f "app.py" ]; then
        python app.py > $LOG_FILE 2>&1 &
        APP_PID=$!
    elif [ -f "manage.py" ]; then
        python manage.py runserver 0.0.0.0:8000 > $LOG_FILE 2>&1 &
        APP_PID=$!
    elif [ -f "package.json" ]; then
        npm start > $LOG_FILE 2>&1 &
        APP_PID=$!
    else
        print_error "No recognizable application entry point found"
        print_status "Please modify the script to add your application startup command"
        exit 1
    fi
    
    # Save PID
    echo $APP_PID > $PID_FILE
    
    # Wait a moment to check if the process started successfully
    sleep 2
    if ps -p $APP_PID > /dev/null 2>&1; then
        print_success "Project started successfully!"
        print_status "PID: $APP_PID"
        print_status "Logs: tail -f $LOG_FILE"
        print_status "Stop with: $0 stop"
    else
        print_error "Failed to start the project"
        print_status "Check logs: cat $LOG_FILE"
        rm -f $PID_FILE
        exit 1
    fi
}

# Function to stop the project
stop_project() {
    print_status "Stopping the project..."
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "No PID file found. Project may not be running."
        return
    fi
    
    PID=$(cat $PID_FILE)
    
    if ps -p $PID > /dev/null 2>&1; then
        print_status "Stopping process with PID: $PID"
        
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
            print_warning "Graceful shutdown failed. Force killing..."
            kill -KILL $PID
        fi
        
        print_success "Project stopped successfully"
    else
        print_warning "Process with PID $PID is not running"
    fi
    
    # Cleanup
    rm -f $PID_FILE
    
    # Stop any additional services (modify as needed)
    # For example, stop Redis, database connections, etc.
    
    # Kill any remaining processes on common ports (optional)
    # print_status "Cleaning up any remaining processes on common ports..."
    # lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    # lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    print_status "Resources freed and cleanup completed"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {install|run|stop}"
    echo ""
    echo "Commands:"
    echo "  install  - Set up the entire project end to end"
    echo "  run      - Start running the project"
    echo "  stop     - Stop the project and save resources"
    echo ""
    echo "Examples:"
    echo "  $0 install"
    echo "  $0 run"
    echo "  $0 stop"
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
    *)
        show_usage
        exit 1
        ;;
esac