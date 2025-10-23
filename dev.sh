#!/bin/bash

# ================================================================================
# Bibliography Development Startup Script
# ================================================================================
# This script starts both backend (FastAPI) and frontend (Next.js) for development
#
# Usage:
#   ./dev.sh              # Start everything
#   ./dev.sh --backend    # Start only backend
#   ./dev.sh --frontend   # Start only frontend
#   ./dev.sh --check      # Run checks only
# ================================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

# ================================================================================
# Helper Functions
# ================================================================================

print_header() {
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
}

print_section() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"

    if [ -n "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
    fi

    if [ -n "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    fi

    echo -e "${GREEN}Cleanup complete. Goodbye!${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ================================================================================
# Prerequisite Checks
# ================================================================================

check_prerequisites() {
    print_header "🔍 Checking Prerequisites"

    local all_good=true

    # Check if we're in the right directory
    print_section "Directory Structure"
    if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
        print_error "backend/ or frontend/ directory not found"
        print_info "Please run this script from the project root"
        exit 1
    fi
    print_success "Project structure looks good"

    # Check Python
    print_section "Python Environment"
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        all_good=false
    else
        PYTHON_VERSION=$(python3 --version)
        print_success "$PYTHON_VERSION"
    fi

    # Check Node.js
    print_section "Node.js Environment"
    if ! command -v node &> /dev/null; then
        print_error "Node.js not found"
        all_good=false
    else
        NODE_VERSION=$(node --version)
        print_success "Node $NODE_VERSION"
    fi

    # Check PostgreSQL
    print_section "PostgreSQL Database"
    if command -v pg_isready &> /dev/null; then
        if pg_isready -h localhost -p 5432 &> /dev/null; then
            print_success "PostgreSQL is running"
        else
            print_warning "PostgreSQL doesn't seem to be running on localhost:5432"
            print_info "Start it with: brew services start postgresql@14 (or your version)"
            all_good=false
        fi
    else
        print_warning "pg_isready not found, skipping PostgreSQL check"
    fi

    # Check backend .env
    print_section "Backend Configuration"
    if [ ! -f "backend/.env" ]; then
        print_error "backend/.env not found"
        print_info "Copy backend/.env.example to backend/.env and configure it"
        all_good=false
    else
        print_success "backend/.env exists"

        # Check for required variables
        if grep -q "DATABASE_URL=" backend/.env && grep -q "SECRET_KEY=" backend/.env; then
            print_success "Required environment variables present"
        else
            print_warning "Some required variables may be missing"
        fi
    fi

    # Check backend venv
    if [ ! -d "backend/venv" ]; then
        print_warning "Backend virtual environment not found"
        print_info "Run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -e ."
    else
        print_success "Backend virtual environment exists"
    fi

    # Check frontend .env.local
    print_section "Frontend Configuration"
    if [ ! -f "frontend/nextjs-app/.env.local" ]; then
        print_warning "frontend/nextjs-app/.env.local not found"
        print_info "It will be created with default values"
        # Create it
        echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/nextjs-app/.env.local
        print_success "Created frontend/nextjs-app/.env.local"
    else
        print_success "frontend/nextjs-app/.env.local exists"
    fi

    # Check frontend node_modules
    if [ ! -d "frontend/nextjs-app/node_modules" ]; then
        print_warning "Frontend dependencies not installed"
        print_info "Run: cd frontend/nextjs-app && npm install"
    else
        print_success "Frontend dependencies installed"
    fi

    echo ""
    if [ "$all_good" = false ]; then
        print_error "Some prerequisites are not met. Please fix the issues above."
        exit 1
    fi

    print_success "All prerequisites satisfied!"
    return 0
}

# ================================================================================
# Start Backend
# ================================================================================

start_backend() {
    print_header "🚀 Starting Backend (FastAPI)"

    cd backend

    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        print_error "Virtual environment not found"
        exit 1
    fi

    print_info "Backend will start on http://localhost:8000"
    print_info "API docs available at http://localhost:8000/docs"
    echo ""

    # Start backend in background
    python main.py --reload > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!

    # Wait a moment to check if it started
    sleep 2
    if kill -0 $BACKEND_PID 2>/dev/null; then
        print_success "Backend started (PID: $BACKEND_PID)"
    else
        print_error "Backend failed to start. Check logs/backend.log"
        exit 1
    fi

    cd ..
}

# ================================================================================
# Start Frontend
# ================================================================================

start_frontend() {
    print_header "🎨 Starting Frontend (Next.js)"

    cd frontend/nextjs-app

    print_info "Frontend will start on http://localhost:3000"
    echo ""

    # Start frontend in background
    npm run dev > ../../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!

    # Wait a moment to check if it started
    sleep 2
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        print_success "Frontend started (PID: $FRONTEND_PID)"
    else
        print_error "Frontend failed to start. Check logs/frontend.log"
        exit 1
    fi

    cd ../..
}

# ================================================================================
# Main Script
# ================================================================================

main() {
    # Parse arguments
    START_BACKEND=true
    START_FRONTEND=true
    CHECK_ONLY=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --backend)
                START_FRONTEND=false
                shift
                ;;
            --frontend)
                START_BACKEND=false
                shift
                ;;
            --check)
                CHECK_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: ./dev.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --backend    Start only backend"
                echo "  --frontend   Start only frontend"
                echo "  --check      Run prerequisite checks only"
                echo "  --help       Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Create logs directory
    mkdir -p logs

    # Run checks
    check_prerequisites

    if [ "$CHECK_ONLY" = true ]; then
        exit 0
    fi

    echo ""
    print_header "📚 Bibliography Development Environment"
    echo ""

    # Start services
    if [ "$START_BACKEND" = true ]; then
        start_backend
        sleep 3
    fi

    if [ "$START_FRONTEND" = true ]; then
        start_frontend
        sleep 3
    fi

    # Show status
    echo ""
    print_header "✨ Development Environment Ready!"
    echo ""

    if [ "$START_BACKEND" = true ]; then
        echo -e "${BOLD}Backend:${NC}"
        echo -e "  ${GREEN}●${NC} http://localhost:8000"
        echo -e "  ${GREEN}●${NC} http://localhost:8000/docs (API documentation)"
        echo ""
    fi

    if [ "$START_FRONTEND" = true ]; then
        echo -e "${BOLD}Frontend:${NC}"
        echo -e "  ${GREEN}●${NC} http://localhost:3000"
        echo ""
    fi

    echo -e "${BOLD}Logs:${NC}"
    if [ "$START_BACKEND" = true ]; then
        echo -e "  Backend:  ${CYAN}tail -f logs/backend.log${NC}"
    fi
    if [ "$START_FRONTEND" = true ]; then
        echo -e "  Frontend: ${CYAN}tail -f logs/frontend.log${NC}"
    fi
    echo ""

    print_info "Press Ctrl+C to stop all services"
    echo ""

    # Keep script running and show live logs
    if [ "$START_BACKEND" = true ] && [ "$START_FRONTEND" = true ]; then
        tail -f logs/backend.log logs/frontend.log
    elif [ "$START_BACKEND" = true ]; then
        tail -f logs/backend.log
    elif [ "$START_FRONTEND" = true ]; then
        tail -f logs/frontend.log
    fi
}

# Run main function
main "$@"
