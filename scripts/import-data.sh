#!/bin/bash

# Import DEVONthink CSV data into the database

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

cd "$(dirname "$0")/.."

print_header "📚 Import DEVONthink Data"

# Check if data file exists
if [ ! -f "data/thumbnail_index.csv" ]; then
    print_error "data/thumbnail_index.csv not found"
    exit 1
fi

# Activate virtual environment
cd backend
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    print_error "Virtual environment not found. Run: cd backend && python3 -m venv venv && pip install -e ."
    exit 1
fi

print_info "Starting import..."
echo ""

# Run import based on arguments
if [ "$1" = "--dry-run" ]; then
    python scripts/import_devonthink_csv.py --dry-run
elif [ "$1" = "--limit" ] && [ -n "$2" ]; then
    python scripts/import_devonthink_csv.py --limit "$2"
elif [ "$1" = "--help" ]; then
    echo "Usage: ./scripts/import-data.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run       Test import without making changes"
    echo "  --limit N       Import only first N records"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/import-data.sh                 # Import all records"
    echo "  ./scripts/import-data.sh --dry-run       # Test run"
    echo "  ./scripts/import-data.sh --limit 10      # Import 10 records"
    exit 0
else
    python scripts/import_devonthink_csv.py --verbose
fi

cd ..
