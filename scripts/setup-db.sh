#!/bin/bash

# Setup and initialize the database

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

print_header() {
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

cd "$(dirname "$0")/.."

print_header "🗄️  Database Setup"

# Check if PostgreSQL is running
if command -v pg_isready &> /dev/null; then
    if ! pg_isready -h localhost -p 5432 &> /dev/null; then
        print_error "PostgreSQL is not running"
        print_info "Start it with: brew services start postgresql@14"
        exit 1
    fi
    print_success "PostgreSQL is running"
else
    print_warning "Cannot check PostgreSQL status (pg_isready not found)"
fi

# Check .env file
if [ ! -f "backend/.env" ]; then
    print_error "backend/.env not found"
    print_info "Copy backend/.env.example to backend/.env and configure DATABASE_URL"
    exit 1
fi

# Activate virtual environment
cd backend
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    print_error "Virtual environment not found"
    print_info "Run: cd backend && python3 -m venv venv && pip install -e ."
    exit 1
fi

print_info "Creating database and tables..."
echo ""

# Create database and tables
python -c "
import asyncio
from app.db import create_db_and_tables

async def main():
    print('Creating tables and indexes...')
    await create_db_and_tables()
    print('✓ Database setup complete!')

asyncio.run(main())
"

print_success "Database initialized successfully!"
echo ""
print_info "Next steps:"
echo "  1. Register a user: ./scripts/create-user.sh"
echo "  2. Import data: ./scripts/import-data.sh"
echo "  3. Start dev environment: ./dev.sh"

cd ..
