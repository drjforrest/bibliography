#!/bin/bash
# Production DEVONthink Sync Script
# This script syncs papers from DEVONthink BIBLIOGRAPHY database to production
# Can be run manually or scheduled via cron

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$HOME/production/hero-evidence-library"
BACKEND_DIR="$PROJECT_DIR/backend"
LOG_FILE="$PROJECT_DIR/logs/devonthink_sync.log"
DATABASE_NAME="BIBLIOGRAPHY"

# Ensure log directory exists
mkdir -p "$PROJECT_DIR/logs"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running on mac-mini
if [ ! -d "$PROJECT_DIR" ]; then
    print_error "Project directory not found: $PROJECT_DIR"
    print_error "This script should be run on mac-mini production server"
    exit 1
fi

print_info "Starting DEVONthink Sync for Production"
print_info "=========================================="
print_info "Database: $DATABASE_NAME"
print_info "Time: $(date)"
print_info ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

# Change to backend directory
cd "$BACKEND_DIR"

# Activate virtual environment
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found in $BACKEND_DIR/venv"
    exit 1
fi

print_info "Activating virtual environment..."
source venv/bin/activate

# Check if uv is available (faster and better dependency resolution)
if command -v uv >/dev/null 2>&1; then
    PACKAGE_MANAGER="uv pip"
    print_info "Using uv for package management"
else
    PACKAGE_MANAGER="pip"
    print_info "Using pip for package management"
fi

# CRITICAL: Fix NumPy compatibility BEFORE any app imports that use torch
print_info "Checking NumPy compatibility..."
NUMPY_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "not_installed")

if [[ "$NUMPY_VERSION" == "not_installed" ]]; then
    print_warning "NumPy not installed, installing compatible version..."
    $PACKAGE_MANAGER install "numpy<2.0" --quiet
    print_success "NumPy installed"
elif [[ $(echo "$NUMPY_VERSION" | cut -d. -f1) -ge 2 ]]; then
    print_warning "NumPy 2.x detected ($NUMPY_VERSION), downgrading for compatibility..."
    $PACKAGE_MANAGER install "numpy<2.0" --upgrade --quiet
    # Verify it worked by checking version again
    NEW_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "error")
    if [[ "$NEW_VERSION" == "error" ]] || [[ $(echo "$NEW_VERSION" | cut -d. -f1) -ge 2 ]]; then
        print_error "Failed to downgrade NumPy. Please run fix_production_numpy.sh manually."
        exit 1
    fi
    print_success "NumPy downgraded from $NUMPY_VERSION to $NEW_VERSION"
else
    print_success "NumPy version is compatible: $NUMPY_VERSION"
fi

# Verify torch can import (this will fail if NumPy is still wrong)
print_info "Verifying NumPy/Torch compatibility..."
if ! python3 -c "import numpy; import torch; print('OK')" >/dev/null 2>&1; then
    print_error "NumPy/Torch compatibility check failed!"
    print_error "Please run: ./scripts/fix_production_numpy.sh"
    exit 1
fi
print_success "NumPy/Torch compatibility verified"

# Check if DEVONthink is running (on the mac-mini, we'll check via API)
print_info "Checking DEVONthink connectivity..."

# Get user ID from database (this will import app modules, so NumPy must be fixed first)
print_info "Getting user ID from database..."
# Suppress all output except the UUID - FlashRank model loading messages go to stdout/stderr
USER_ID=$(python3 -c "
import asyncio
import sys
import os
# Suppress warnings and info messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
sys.path.insert(0, '.')
# Redirect stdout temporarily to capture only UUID
original_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from app.db import User
from app.config import config

async def get_user():
    engine = create_async_engine(config.DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(select(User))
        users = result.fetchall()
        if users:
            sys.stdout = original_stdout
            print(users[0].id)
            sys.stdout = open(os.devnull, 'w')
    await engine.dispose()

asyncio.run(get_user())
sys.stdout.close()
" 2>&1 | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)

# Validate UUID format
if [ -z "$USER_ID" ]; then
    print_error "No user found in database. Please create a user first."
    exit 1
fi

# Validate it's a proper UUID format
if ! echo "$USER_ID" | grep -qE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
    print_error "Invalid user ID format: $USER_ID"
    print_error "User ID extraction may have captured extra output. Check database connection."
    exit 1
fi

print_success "Found user ID: $USER_ID"

# Check if DEVONthink is accessible (we'll check this via the API endpoint)
print_info "Checking DEVONthink connection..."

# Run the sync using the migration CLI
print_info "Starting DEVONthink sync..."
print_info "This may take several hours for ~2700+ records..."

python3 start_migration_cli.py \
    --database "$DATABASE_NAME" \
    --user-id "$USER_ID" \
    --redis-url "redis://localhost:6379/0" 2>&1 | tee -a "$LOG_FILE"

SYNC_EXIT_CODE=${PIPESTATUS[0]}

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    print_success "Sync completed successfully!"
    
    # Get final counts
    print_info "Getting final record counts..."
    FINAL_COUNT=$(python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine
from app.db import ScientificPaper
from app.config import config

async def count_papers():
    engine = create_async_engine(config.DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(
            select(func.count(ScientificPaper.id))
            .where(ScientificPaper.dt_source_uuid.isnot(None))
        )
        count = result.scalar()
        print(count)
    await engine.dispose()

asyncio.run(count_papers())
" 2>/dev/null)
    
    print_success "Total DEVONthink papers in database: $FINAL_COUNT"
else
    print_error "Sync failed with exit code: $SYNC_EXIT_CODE"
    print_error "Check logs at: $LOG_FILE"
    exit $SYNC_EXIT_CODE
fi

print_info ""
print_info "Sync completed at: $(date)"
print_info "Log file: $LOG_FILE"
print_success "=========================================="

