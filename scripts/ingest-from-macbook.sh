#!/bin/bash

# ingest-from-macbook.sh
# Runs on Mac-mini to ingest PDFs transferred from MacBook
#
# This script:
# 1. Monitors the staging directory for incoming PDFs
# 2. Organizes them into UUID-based storage structure
# 3. Triggers FastAPI sync endpoint to process metadata and vectorize

set -e

# Configuration
# Auto-detect if running in dev or production based on directory structure
if [ -d "${HOME}/dev/devprojects/bibliography/backend" ]; then
    # Development environment
    BACKEND_DIR="${HOME}/dev/devprojects/bibliography/backend"
    STAGING_DIR="${HOME}/dev/devprojects/bibliography/data/incoming"
    BACKEND_URL="http://localhost:8000"
    ENV_MODE="development"
elif [ -d "/opt/bibliography/backend" ]; then
    # Production environment
    BACKEND_DIR="/opt/bibliography/backend"
    STAGING_DIR="/opt/bibliography/data/incoming"
    BACKEND_URL="http://localhost:8000"
    ENV_MODE="production"
else
    # Try current directory as fallback
    BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)/backend"
    STAGING_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/incoming"
    BACKEND_URL="http://localhost:8000"
    ENV_MODE="auto-detected"
fi

LOG_FILE="${HOME}/.bibliography_ingest.log"

# Colors for output
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

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Ensure staging directory exists
setup_staging_directory() {
    if [ ! -d "$STAGING_DIR" ]; then
        print_info "Creating staging directory: $STAGING_DIR"
        mkdir -p "$STAGING_DIR"
        print_success "Created staging directory"
    fi
}

# Check if backend is running
check_backend() {
    if curl -s "${BACKEND_URL}/api/v1/health" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Start backend if not running
ensure_backend_running() {
    if check_backend; then
        print_success "Backend is running at ${BACKEND_URL}"
        return 0
    fi

    print_warning "Backend is not running"
    print_info "Starting backend..."

    cd "$BACKEND_DIR"

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found in ${BACKEND_DIR}"
        print_info "Please set up the backend first:"
        print_info "  cd ${BACKEND_DIR}"
        print_info "  python3 -m venv venv"
        print_info "  source venv/bin/activate"
        print_info "  pip install -e ."
        return 1
    fi

    # Start backend in background
    source venv/bin/activate
    nohup python main.py > "${HOME}/.bibliography_backend.log" 2>&1 &
    local backend_pid=$!

    print_info "Backend starting (PID: ${backend_pid})..."

    # Wait up to 30 seconds for backend to be ready
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if check_backend; then
            print_success "Backend is ready"
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
    done

    print_error "Backend failed to start within 30 seconds"
    print_info "Check logs: ${HOME}/.bibliography_backend.log"
    return 1
}

# Process CSV file if present
process_csv() {
    local csv_file="${STAGING_DIR}/active_library.csv"

    if [ ! -f "$csv_file" ]; then
        return 0
    fi

    print_info "Found active_library.csv - processing metadata..."

    cd "$BACKEND_DIR"
    source venv/bin/activate

    # Run CSV import script
    if python scripts/import_active_library_csv.py "$csv_file"; then
        print_success "CSV metadata imported successfully"
        log "Imported metadata from active_library.csv"

        # Archive the CSV file after successful import
        local archive_dir="${STAGING_DIR}/processed"
        mkdir -p "$archive_dir"
        local timestamp=$(date +%Y%m%d_%H%M%S)
        mv "$csv_file" "${archive_dir}/active_library_${timestamp}.csv"
        print_info "Archived CSV to processed folder"
    else
        print_error "CSV import failed - check logs"
        log "ERROR: CSV import failed"
        return 1
    fi

    return 0
}

# Process PDF files from staging directory
process_pdfs() {
    local pdf_count=$(find "$STAGING_DIR" -name "*.pdf" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [ "$pdf_count" -eq 0 ]; then
        print_info "No PDF files to process"
        return 0
    fi

    print_info "Found ${pdf_count} PDF file(s) to process"

    # First, check if we have a CSV file - if so, use it for metadata
    if [ -f "${STAGING_DIR}/active_library.csv" ]; then
        print_info "Using CSV metadata for import..."
        process_csv
        # CSV import handles PDFs, so we're done
        print_success "Import via CSV complete"
        return 0
    fi

    # No CSV - fall back to regular PDF processing
    cd "$BACKEND_DIR"
    source venv/bin/activate

    # Move PDFs to the watched folder for automatic processing
    local watched_folder="${BACKEND_DIR}/data/watched"
    mkdir -p "$watched_folder"

    local processed=0
    local failed=0

    for pdf in "$STAGING_DIR"/*.pdf; do
        [ -f "$pdf" ] || continue

        local filename=$(basename "$pdf")
        print_info "Processing: $filename"

        # Move to watched folder
        if mv "$pdf" "$watched_folder/$filename"; then
            processed=$((processed + 1))
            log "Moved $filename to watched folder"
        else
            failed=$((failed + 1))
            print_error "Failed to move $filename"
            log "ERROR: Failed to move $filename"
        fi
    done

    print_success "Moved ${processed} file(s) to watched folder"

    if [ $failed -gt 0 ]; then
        print_warning "${failed} file(s) failed to process"
    fi

    # The folder watcher service will automatically process these files
    # Alternatively, trigger manual ingestion via API if folder watcher is not running
    trigger_manual_ingestion

    return 0
}

# Trigger manual ingestion via Python script
trigger_manual_ingestion() {
    print_info "Triggering manual ingestion via Python script..."

    cd "$BACKEND_DIR"
    source venv/bin/activate

    # Create a simple Python script to ingest files
    python3 << 'EOF'
import asyncio
import sys
from pathlib import Path
from app.services.folder_watcher import process_watched_folder_once

async def main():
    """Process all files in watched folder once"""
    try:
        results = await process_watched_folder_once()
        if results:
            print(f"✓ Processed {results['processed']} files")
            if results.get('errors'):
                print(f"⚠ {len(results['errors'])} errors occurred")
                for error in results['errors']:
                    print(f"  - {error}")
        else:
            print("ℹ No files to process")
        return 0
    except Exception as e:
        print(f"✗ Error during ingestion: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
EOF

    if [ $? -eq 0 ]; then
        print_success "Ingestion completed"
        log "Manual ingestion completed successfully"
    else
        print_error "Ingestion failed"
        log "ERROR: Manual ingestion failed"
    fi
}

# Watch mode - continuously monitor staging directory
watch_mode() {
    print_header "Bibliography Ingestion - Watch Mode"
    print_info "Monitoring: $STAGING_DIR"
    print_info "Backend: ${BACKEND_URL}"
    print_info "Press Ctrl+C to stop"
    echo ""

    log "Watch mode started"

    ensure_backend_running

    local last_count=0

    while true; do
        local current_count=$(find "$STAGING_DIR" -name "*.pdf" -type f 2>/dev/null | wc -l | tr -d ' ')

        if [ "$current_count" -gt 0 ] && [ "$current_count" != "$last_count" ]; then
            echo ""
            print_info "Detected new files..."
            process_pdfs
            echo ""
            print_info "Waiting for new files... (checking every 10s)"
        fi

        last_count=$current_count
        sleep 10
    done
}

# One-time ingestion mode
oneshot_mode() {
    print_header "Bibliography Ingestion - One-time Process"
    print_info "Environment: ${ENV_MODE}"
    print_info "Backend directory: ${BACKEND_DIR}"

    setup_staging_directory

    if ! ensure_backend_running; then
        print_error "Cannot proceed without backend"
        exit 1
    fi

    process_pdfs

    print_success "Ingestion complete!"
}

# Main script
main() {
    case "${1:-oneshot}" in
        --watch|-w)
            setup_staging_directory
            watch_mode
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Ingest PDFs from staging directory into bibliography system"
            echo ""
            echo "Options:"
            echo "  --watch, -w     Watch mode - continuously monitor and ingest"
            echo "  --help, -h      Show this help message"
            echo "  (no options)    One-time ingestion of current files"
            echo ""
            echo "Configuration:"
            echo "  Staging:  $STAGING_DIR"
            echo "  Backend:  $BACKEND_URL"
            echo ""
            exit 0
            ;;
        *)
            oneshot_mode
            ;;
    esac
}

main "$@"
