#!/bin/bash

# hero-evidence-library Production Deployment Script
# Deploys to mac-mini with SSH tunnel for PDF access from dev machine
# Backend on port 8400, Frontend on port 3400, PostgreSQL on 5432

set -e

echo "🔍 hero-evidence-library Production Deployment"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVER_USER="jforrest"
SERVER_HOST="mac-mini"
SERVER_PATH="~/production/hero-evidence-library"
BACKEND_PORT="8400"
FRONTEND_PORT="3400"
DB_PORT="5432"

# SSH Tunnel for PDF access (mac-mini will connect back to dev machine)
DEV_PDF_PORT="9999"  # Port on dev machine to serve PDFs via SSH tunnel

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    print_error "This script should be run from the hero-evidence-library project root directory"
    exit 1
fi

# Validate project structure
if [ ! -d "frontend" ]; then
    print_error "frontend directory not found"
    exit 1
fi

if [ ! -d "backend" ]; then
    print_error "backend directory not found"
    exit 1
fi

# Check for frontend/nextjs-app structure
if [ ! -d "frontend/nextjs-app" ]; then
    print_error "frontend/nextjs-app directory not found"
    exit 1
fi

print_status "Building frontend..."
cd frontend/nextjs-app
npm install
npm run build
cd ../..

print_status "Preparing backend..."
# Just verify requirements exist, don't install locally
if [ ! -f "backend/requirements.txt" ]; then
    print_error "backend/requirements.txt not found"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if production .env exists
if [ ! -f ".env.production" ]; then
    print_warning ".env.production not found - will be created on server"
fi

print_status "📤 Syncing local changes to production..."
rsync -avz -e "ssh -o Ciphers=aes256-gcm@openssh.com" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='logs' \
    --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env.local' \
    --exclude='.env' \
    --exclude='data/pdfs' \
    --exclude='backend/.flashrank_cache' \
    --exclude='.flashrank_cache' \
    --exclude='frontend/nextjs-app/.next' \
    "$SCRIPT_DIR/" ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/

# Copy production environment files
if [ -f ".env.production" ]; then
    print_status "Copying production .env template..."
    scp -o Ciphers=aes256-gcm@openssh.com .env.production ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/backend/.env.template
    
    # If local secrets file exists, merge it
    if [ -f ".env.production.local" ]; then
        print_status "Copying production secrets..."
        scp -o Ciphers=aes256-gcm@openssh.com .env.production.local ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/backend/.env.secrets
        print_status "✓ Merging environment files on server..."
        ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH}/backend && { cat .env.template; echo; cat .env.secrets; } > .env && rm .env.secrets"
    else
        print_warning "⚠ No .env.production.local found - copying template only"
        ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH}/backend && cp .env.template .env"
        print_warning "⚠ You'll need to manually update secrets in backend/.env on the server"
    fi
else
    print_warning "⚠ No .env.production file found - make sure to set up environment variables on the server"
fi

# Copy frontend production environment
if [ -f "frontend/nextjs-app/.env.production.local" ]; then
    print_status "Copying frontend production secrets..."
    scp -o Ciphers=aes256-gcm@openssh.com frontend/nextjs-app/.env.production.local ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/frontend/nextjs-app/.env.local
fi

print_status "Setting up production environment and restarting services..."
ssh ${SERVER_USER}@${SERVER_HOST} "
    cd ${SERVER_PATH}

    # Set production environment
    export ENVIRONMENT=production
    export DEBUG=false
    export LOG_LEVEL=INFO

    # Stop existing hero-evidence-library services and clear ports
    echo 'Stopping existing hero-evidence-library services and clearing ports...'

    # Kill processes by name pattern
    pkill -f 'uvicorn.*main:app.*${BACKEND_PORT}' || true
    pkill -f 'next.*${FRONTEND_PORT}' || true
    pkill -f 'npm.*start.*${FRONTEND_PORT}' || true

    # Force kill any processes using our ports
    echo 'Clearing port ${BACKEND_PORT} (backend)...'
    lsof -ti:${BACKEND_PORT} | xargs kill -9 2>/dev/null || echo 'Port ${BACKEND_PORT} is free'

    echo 'Clearing port ${FRONTEND_PORT} (frontend)...'
    lsof -ti:${FRONTEND_PORT} | xargs kill -9 2>/dev/null || echo 'Port ${FRONTEND_PORT} is free'

    # Wait a moment for ports to clear
    sleep 2

    # Verify ports are free
    if lsof -i:${BACKEND_PORT} >/dev/null 2>&1; then
        echo '⚠ Warning: Port ${BACKEND_PORT} still in use'
        lsof -i:${BACKEND_PORT}
    else
        echo '✓ Port ${BACKEND_PORT} is available'
    fi

    if lsof -i:${FRONTEND_PORT} >/dev/null 2>&1; then
        echo '⚠ Warning: Port ${FRONTEND_PORT} still in use'
        lsof -i:${FRONTEND_PORT}
    else
        echo '✓ Port ${FRONTEND_PORT} is available'
    fi

    # Ensure Python 3.12 is available via pyenv
    echo 'Setting up Python 3.12 via pyenv...'
    export PYENV_ROOT=\$HOME/.pyenv
    export PATH=\"\$PYENV_ROOT/shims:\$PATH\"

    if command -v pyenv &> /dev/null; then
        # Try to use pyenv's Python 3.12
        if pyenv versions | grep -q '3.12'; then
            PYTHON_CMD=\$(pyenv which python3)
            echo \"✓ Using pyenv Python: \$PYTHON_CMD\"
        else
            echo '⚠ Python 3.12 not found in pyenv, using system python3'
            PYTHON_CMD='python3'
        fi
    else
        # Fallback to direct pyenv shim path
        if [ -f \"\$PYENV_ROOT/shims/python3\" ]; then
            PYTHON_CMD=\"\$PYENV_ROOT/shims/python3\"
            echo \"✓ Using pyenv shim: \$PYTHON_CMD\"
        else
            echo '⚠ pyenv not found, using system python3'
            PYTHON_CMD='python3'
        fi
    fi

    # Install/update backend dependencies
    echo 'Setting up backend environment...'
    cd backend

    # Recreate venv to ensure correct Python version
    if [ -d venv ]; then
        echo 'Removing old venv...'
        rm -rf venv
    fi
    echo \"Creating new venv with \$PYTHON_CMD...\"
    \$PYTHON_CMD -m venv venv
    source venv/bin/activate

    # Verify Python version in venv
    python --version

    echo 'Installing backend dependencies...'
    pip install --upgrade pip
    pip install -r requirements.txt

    # Check if .env exists
    if [ ! -f .env ]; then
        echo '⚠ No .env file found in backend/ - using environment variables'
    fi

    # Start backend service
    echo 'Starting hero-evidence-library backend on port ${BACKEND_PORT}...'
    BACKEND_DIR=\$(pwd)
    nohup env PYTHONPATH=\$BACKEND_DIR ./venv/bin/python -m uvicorn app.app:app --host 0.0.0.0 --port ${BACKEND_PORT} > ../hero_evidence_library_backend.log 2>&1 &
    
    # Setup and start frontend
    echo 'Setting up frontend environment...'
    cd ../frontend/nextjs-app

    # Load nvm to ensure npm is available
    export NVM_DIR=\"\$HOME/.nvm\"
    [ -s \"\$NVM_DIR/nvm.sh\" ] && source \"\$NVM_DIR/nvm.sh\"
    
    # Use Node 22 to match dev environment
    nvm install 22 2>/dev/null || true
    nvm use 22 2>/dev/null || nvm use default

    # Check if .env.local exists (copied from .env.production.local earlier)
    if [ ! -f .env.local ]; then
        echo 'Creating minimal production .env.local for frontend...'
        cat > .env.local << EOF
# Frontend .env.local for hero-evidence-library Project - Production
NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
EOF
    else
        echo '✓ Using .env.local copied from production secrets'
    fi

    npm install --production

    # Start frontend service (already built locally)
    echo 'Starting hero-evidence-library frontend on port ${FRONTEND_PORT}...'
    nohup npm run start -- -p ${FRONTEND_PORT} > ../../hero_evidence_library_frontend.log 2>&1 &

    echo 'hero-evidence-library services started:'
    echo '  - Backend: http://localhost:${BACKEND_PORT}'
    echo '  - Frontend: http://localhost:${FRONTEND_PORT}'
    echo '  - Database: PostgreSQL on port ${DB_PORT}'
    echo '  - Logs: hero_evidence_library_backend.log, hero_evidence_library_frontend.log'
"

print_status "hero-evidence-library has been deployed to production server!"
print_status ""
print_status "Configuration:"
print_status "  - Server path: ${SERVER_PATH}"
print_status "  - Backend port: ${BACKEND_PORT}"
print_status "  - Frontend port: ${FRONTEND_PORT}"
print_status "  - Database: PostgreSQL on port ${DB_PORT}"
print_status ""
print_warning "⚠ IMPORTANT: PDFs are still on dev machine"
print_warning "To enable PDF access from production, you need to:"
print_warning "1. Run ./scripts/setup-ssh-tunnel.sh on THIS (dev) machine"
print_warning "2. Configure backend .env on production with SSH tunnel settings"
print_status ""
print_status "Next steps:"
print_status "1. Initialize database: ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && ./scripts/init-production-db.sh'"
print_status "2. Set up SSH tunnel for PDFs: ./scripts/setup-ssh-tunnel.sh"
print_status "3. Access via Cloudflare tunnel at: library.counterforce-hero.tech"
print_status ""
print_status "🎉 Deployment complete!"
