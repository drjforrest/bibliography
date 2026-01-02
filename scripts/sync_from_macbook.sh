#!/bin/bash
# Sync DEVONthink from MacBook (where DEVONthink is running) to Production Database
# This syncs to production but runs from your dev machine where DEVONthink is accessible

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
LOG_FILE="$PROJECT_DIR/logs/devonthink_sync_macbook.log"
DATABASE_NAME="BIBLIOGRAPHY"

# Ensure log directory exists
mkdir -p "$PROJECT_DIR/logs"

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

print_info "Starting DEVONthink Sync from MacBook"
print_info "=========================================="
print_info "Database: $DATABASE_NAME"
print_info "Target: Production Database"
print_info "Time: $(date)"
print_info ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

# Change to backend directory
cd "$BACKEND_DIR"

# Set tokenizer parallelism to avoid warnings
export TOKENIZERS_PARALLELISM=false

# Set LLM API base URL (LMStudio)
# Can be overridden by environment variable FAST_LLM_API_BASE
if [ -z "$FAST_LLM_API_BASE" ]; then
    export FAST_LLM_API_BASE="http://192.168.1.88:1234/v1"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

print_info "Activating virtual environment..."
source venv/bin/activate

# Verify Python is working
if ! python3 --version >/dev/null 2>&1; then
    print_error "Python is not working in virtual environment"
    exit 1
fi

# Install/upgrade dependencies if needed
print_info "Ensuring dependencies are installed..."
if [ ! -f "venv/.dependencies_installed" ]; then
    print_info "Installing dependencies (first time only)..."
    pip install --upgrade pip
    pip install -e . 2>&1 | grep -v "already satisfied" || true
    touch venv/.dependencies_installed
    print_success "Dependencies installed"
fi

# Determine package manager - prefer pip over uv to avoid path issues
# Use pip directly in venv for reliability
PACKAGE_MANAGER="pip"
print_info "Using pip for package management"

# Check NumPy compatibility
print_info "Checking NumPy compatibility..."
NUMPY_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "not_installed")

if [[ "$NUMPY_VERSION" == "not_installed" ]]; then
    print_info "NumPy not installed, installing compatible version..."
    $PACKAGE_MANAGER install "numpy<2.0" --quiet
    print_success "NumPy installed"
elif [[ $(echo "$NUMPY_VERSION" | cut -d. -f1) -ge 2 ]]; then
    print_warning "NumPy 2.x detected ($NUMPY_VERSION), downgrading for compatibility..."
    $PACKAGE_MANAGER install "numpy<2.0" --upgrade --quiet
    NEW_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null)
    print_success "NumPy downgraded to $NEW_VERSION"
else
    print_success "NumPy version is compatible: $NUMPY_VERSION"
fi

# Verify torch can import
print_info "Verifying NumPy/Torch compatibility..."
if ! python3 -c "import numpy; import torch; print('OK')" >/dev/null 2>&1; then
    print_error "NumPy/Torch compatibility check failed!"
    print_error "Run: pip install 'numpy<2.0' --upgrade"
    exit 1
fi

# Set LLM API base URL (LMStudio) - default to 192.168.1.88:1234
# Can be overridden by environment variable FAST_LLM_API_BASE
if [ -z "$FAST_LLM_API_BASE" ]; then
    export FAST_LLM_API_BASE="http://192.168.1.88:1234/v1"
    print_info "Using LLM API: $FAST_LLM_API_BASE"
fi

# Set LLM model name (can be overridden by environment variable FAST_LLM)
# Note: LM Studio will use whatever model you have loaded, regardless of the name here
# The name is just used in the API request
# For 32GB RAM: 7B models work great (like Mistral-7B)
if [ -z "$FAST_LLM" ]; then
    export FAST_LLM="mistral-7b-v0.1"
    print_info "Using LLM model: $FAST_LLM (LM Studio will use whatever model you have loaded)"
    print_info "If your model name is different in LM Studio, that's OK - it will use the loaded model"
fi

# Allow overriding database URL for production
if [ -n "$DATABASE_URL" ]; then
    print_info "Using provided DATABASE_URL for production database"
    # Show masked version for confirmation
    MASKED_URL=$(echo "$DATABASE_URL" | sed 's/:[^:]*@/:***@/')
    print_info "Database: $MASKED_URL"
    export DATABASE_URL
else
    print_warning "DATABASE_URL not set. Will use .env file (local database)."
    print_warning "To sync to production, set: export DATABASE_URL='postgresql+asyncpg://postgres:postgres@mac-mini:5432/hero_evidence_library_prod'"
fi

# Get user ID from production database
print_info "Getting user ID from database..."
# Explicitly pass DATABASE_URL to Python, ensuring it's used even if .env exists
USER_ID_OUTPUT=$(env DATABASE_URL="$DATABASE_URL" python3 -c "
import asyncio
import sys
import os
sys.path.insert(0, '.')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# IMPORTANT: Use DATABASE_URL from environment first (takes precedence over .env)
# This allows overriding the database URL from command line
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    # Fall back to config if not in environment
    from app.config import config
    db_url = config.DATABASE_URL

# Test connection first
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine
from app.db import User

async def test_and_get_user():
    try:
        engine = create_async_engine(db_url)
        # Test connection with a simple query
        async with engine.begin() as conn:
            # Test database connection
            result = await conn.execute(text('SELECT 1'))
            result.fetchone()
            
            # Get database name for confirmation
            db_result = await conn.execute(text('SELECT current_database()'))
            db_name = db_result.scalar()
            print(f'Connected to database: {db_name}', file=sys.stderr)
            
            # Get user count
            count_result = await conn.execute(select(User))
            users = count_result.fetchall()
            user_count = len(users)
            print(f'Found {user_count} users in database', file=sys.stderr)
            
            if users:
                print(users[0].id)
            else:
                print('NO_USERS_FOUND', file=sys.stderr)
        await engine.dispose()
    except Exception as e:
        print(f'Connection error: {str(e)}', file=sys.stderr)
        raise

asyncio.run(test_and_get_user())
" 2>&1)

# Extract UUID or error
USER_ID=$(echo "$USER_ID_OUTPUT" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
ERROR_OUTPUT=$(echo "$USER_ID_OUTPUT" | grep -v -E '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

# Show connection info if available
if echo "$USER_ID_OUTPUT" | grep -q "Connected to database:"; then
    echo "$USER_ID_OUTPUT" | grep "Connected to database:"
fi
if echo "$USER_ID_OUTPUT" | grep -q "Found.*users"; then
    echo "$USER_ID_OUTPUT" | grep "Found.*users"
fi

# Show any connection errors
if echo "$USER_ID_OUTPUT" | grep -q "Connection error:"; then
    echo "$USER_ID_OUTPUT" | grep "Connection error:"
    print_error ""
    print_error "Database connection failed. You need to set up an SSH tunnel:"
    print_error ""
    print_error "Option 1: Use the setup script (recommended):"
    print_error "  ./scripts/setup_db_tunnel.sh"
    print_error ""
    print_error "Option 2: Manual SSH tunnel:"
    print_error "  ssh -L 5433:localhost:5432 mac-mini"
    print_error "  (keep that terminal open, then in another terminal:)"
    print_error "  # Option 1: SSH tunnel (localhost:5433)"
    print_error "  export DATABASE_URL='postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/hero_evidence_library_prod'"
    print_error ""
    print_error "  # Option 2: Direct connection (if PostgreSQL allows network access)"
    print_error "  export DATABASE_URL='postgresql+asyncpg://postgres:postgres@192.168.1.69:5432/hero_evidence_library_prod'"
    print_error "  ./scripts/sync_from_macbook.sh"
    exit 1
fi

if [ -z "$USER_ID" ]; then
    print_error "No user found in database."
    if echo "$USER_ID_OUTPUT" | grep -q "NO_USERS_FOUND"; then
        print_error "Connection succeeded but database has no users."
        print_error "You may need to create a user first on the production server."
    else
        print_error "Could not extract user ID from database."
        echo "$ERROR_OUTPUT"
    fi
    exit 1
fi

if ! echo "$USER_ID" | grep -qE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
    print_error "Invalid user ID format: $USER_ID"
    exit 1
fi

print_success "Found user ID: $USER_ID"

# Check if DEVONthink is running (local check)
print_info "Checking if DEVONthink is running..."
if pgrep -f "DEVONthink" >/dev/null; then
    print_success "DEVONthink is running"
else
    print_error "DEVONthink is not running on this machine!"
    print_error "Please start DEVONthink and try again"
    exit 1
fi

# Check which DEVONthink database is open
print_info "Checking which DEVONthink database is open..."
DB_CHECK_OUTPUT=$(python3 -c "
import asyncio
import sys
import os
sys.path.insert(0, '.')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from app.services.devonthink_mcp_client_real_v2 import DevonthinkMCPClientRealV2

async def check_databases():
    try:
        client = DevonthinkMCPClientRealV2()
        databases = await client.get_open_databases()
        if databases:
            db_names = [db.get('name', 'Unknown') for db in databases]
            print('OPEN_DATABASES:' + ','.join(db_names))
            for db in databases:
                name = db.get('name', 'Unknown')
                uuid = db.get('uuid', 'Unknown')
                print(f'DATABASE:{name}:{uuid}')
        else:
            print('NO_DATABASES')
        await client.close()
    except Exception as e:
        print(f'ERROR:{str(e)}', file=sys.stderr)
        sys.exit(1)

asyncio.run(check_databases())
" 2>&1)

# Parse the output
OPEN_DBS_LINE=$(echo "$DB_CHECK_OUTPUT" | grep "^OPEN_DATABASES:" || echo "")
DB_ERROR=$(echo "$DB_CHECK_OUTPUT" | grep "^ERROR:" || echo "")

if [ -n "$DB_ERROR" ]; then
    print_error "Failed to check DEVONthink databases:"
    echo "$DB_CHECK_OUTPUT"
    print_error ""
    print_error "This might be a temporary MCP connection issue. Continuing anyway..."
    print_warning "Make sure '$DATABASE_NAME' is open in DEVONthink!"
elif [ -z "$OPEN_DBS_LINE" ]; then
    print_error "Could not determine which databases are open"
    print_warning "Make sure '$DATABASE_NAME' is open in DEVONthink!"
else
    # Extract database names
    OPEN_DBS=$(echo "$OPEN_DBS_LINE" | sed 's/^OPEN_DATABASES://')
    print_info "Open DEVONthink databases: $OPEN_DBS"
    
    # Check if BIBLIOGRAPHY is in the list
    if echo "$OPEN_DBS" | grep -qi "$DATABASE_NAME"; then
        print_success "✓ '$DATABASE_NAME' database is open in DEVONthink"
    else
        print_error "✗ '$DATABASE_NAME' database is NOT open in DEVONthink!"
        print_error ""
        print_error "Currently open databases: $OPEN_DBS"
        print_error ""
        print_error "Please:"
        print_error "  1. Open DEVONthink"
        print_error "  2. Open the '$DATABASE_NAME' database"
        print_error "  3. Run this script again"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Aborted by user"
            exit 1
        else
            print_warning "Continuing with sync (user confirmed)..."
        fi
    fi
fi

# Test database connection if DATABASE_URL is provided
if [ -n "$DATABASE_URL" ]; then
    print_info "Testing connection to production database..."
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ]; then
        print_info "Testing connection to $DB_HOST:$DB_PORT..."
        if timeout 5 bash -c "echo > /dev/tcp/$DB_HOST/$DB_PORT" 2>/dev/null; then
            print_success "Database connection test passed"
        else
            print_warning "Cannot connect to $DB_HOST:$DB_PORT"
            print_warning "You may need to use SSH tunnel: ssh -L 5433:localhost:5432 mac-mini"
            print_warning "Then use: export DATABASE_URL='postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/hero_evidence_library_prod'"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
fi

# Run the sync
print_info "Starting DEVONthink sync..."
print_info "This may take several hours for ~2700+ records..."
print_info ""

# Make sure DATABASE_URL is available to the migration script
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL
    export FAST_LLM_API_BASE
    export FAST_LLM
    DATABASE_URL="$DATABASE_URL" FAST_LLM_API_BASE="$FAST_LLM_API_BASE" FAST_LLM="$FAST_LLM" python3 start_migration_cli.py \
        --database "$DATABASE_NAME" \
        --user-id "$USER_ID" \
        --redis-url "redis://localhost:6379/0" 2>&1 | tee -a "$LOG_FILE"
else
    python3 start_migration_cli.py \
        --database "$DATABASE_NAME" \
        --user-id "$USER_ID" \
        --redis-url "redis://localhost:6379/0" 2>&1 | tee -a "$LOG_FILE"
fi

SYNC_EXIT_CODE=${PIPESTATUS[0]}

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    print_success "Sync completed successfully!"
else
    print_error "Sync failed with exit code: $SYNC_EXIT_CODE"
    print_error "Check logs at: $LOG_FILE"
    exit $SYNC_EXIT_CODE
fi

print_info ""
print_info "Sync completed at: $(date)"
print_info "Log file: $LOG_FILE"
print_success "=========================================="

