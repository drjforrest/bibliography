#!/bin/bash

# sync-to-macmini.sh
# Sync PDFs from MacBook DEVONthink export to Mac-mini for processing
#
# This script runs on the MacBook and:
# 1. Monitors the Desktop export folder for PDFs
# 2. Transfers them to Mac-mini via SSH/rsync
# 3. Triggers the Mac-mini ingestion process

set -e

# Configuration
MAC_MINI_IP="100.75.201.24"
MAC_MINI_USER="${MAC_MINI_USER:-drjforrest}"  # Override with env var if different
SOURCE_DIR="${HOME}/PDFs/Evidence_Library_Sync"
REMOTE_STAGING_DIR="/Users/drjforrest/dev/devprojects/bibliography/data/incoming"
LOG_FILE="${HOME}/.bibliography_sync.log"

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

# Check if source directory exists
check_source_directory() {
    if [ ! -d "$SOURCE_DIR" ]; then
        print_error "Source directory does not exist: $SOURCE_DIR"
        print_info "Creating source directory..."
        mkdir -p "$SOURCE_DIR"
        print_success "Created $SOURCE_DIR"
        print_info "Please export PDFs from DEVONthink to this folder"
        return 1
    fi
    return 0
}

# Test SSH connection to Mac-mini
test_connection() {
    print_info "Testing connection to Mac-mini at ${MAC_MINI_IP}..."
    if ssh -o ConnectTimeout=5 "${MAC_MINI_USER}@${MAC_MINI_IP}" "echo 'Connection successful'" &>/dev/null; then
        print_success "Connected to Mac-mini"
        return 0
    else
        print_error "Cannot connect to Mac-mini at ${MAC_MINI_IP}"
        print_info "Please ensure:"
        print_info "  1. Tailscale is running on both machines"
        print_info "  2. SSH is enabled on Mac-mini (System Settings > General > Sharing > Remote Login)"
        print_info "  3. SSH keys are configured for passwordless login"
        return 1
    fi
}

# Ensure remote staging directory exists
setup_remote_directory() {
    print_info "Setting up remote staging directory..."
    if ssh "${MAC_MINI_USER}@${MAC_MINI_IP}" "mkdir -p ${REMOTE_STAGING_DIR}"; then
        print_success "Remote staging directory ready: ${REMOTE_STAGING_DIR}"
        return 0
    else
        print_error "Failed to create remote staging directory"
        return 1
    fi
}

# Sync files using rsync
sync_files() {
    local pdf_count=$(find "$SOURCE_DIR" -name "*.pdf" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [ "$pdf_count" -eq 0 ]; then
        print_warning "No PDF files found in $SOURCE_DIR"
        return 0
    fi

    print_info "Found ${pdf_count} PDF file(s) to sync"

    # Use rsync for efficient transfer
    # -a: archive mode (preserves permissions, timestamps)
    # -v: verbose
    # -z: compress during transfer
    # -h: human-readable progress
    # --progress: show progress
    # --remove-source-files: delete source files after successful transfer

    print_info "Starting rsync transfer..."

    if rsync -avzh --progress \
        --include='*.pdf' \
        --exclude='*' \
        --remove-source-files \
        "$SOURCE_DIR/" \
        "${MAC_MINI_USER}@${MAC_MINI_IP}:${REMOTE_STAGING_DIR}/"; then

        print_success "Successfully transferred ${pdf_count} file(s)"
        log "Synced ${pdf_count} files to Mac-mini"

        # Clean up empty directories
        find "$SOURCE_DIR" -type d -empty -delete 2>/dev/null || true

        return 0
    else
        print_error "Rsync transfer failed"
        log "ERROR: Rsync transfer failed"
        return 1
    fi
}

# Trigger remote processing
trigger_ingestion() {
    print_info "Triggering ingestion on Mac-mini..."

    # SSH into Mac-mini and trigger the ingestion script
    if ssh "${MAC_MINI_USER}@${MAC_MINI_IP}" \
        "cd /Users/drjforrest/dev/devprojects/bibliography && ./scripts/ingest-from-macbook.sh"; then
        print_success "Ingestion triggered successfully"
        log "Triggered ingestion on Mac-mini"
        return 0
    else
        print_warning "Could not trigger ingestion automatically"
        print_info "Files are on Mac-mini at: ${REMOTE_STAGING_DIR}"
        print_info "Run ingestion manually: ssh ${MAC_MINI_USER}@${MAC_MINI_IP} 'cd /Users/drjforrest/dev/devprojects/bibliography && ./scripts/ingest-from-macbook.sh'"
        return 1
    fi
}

# Watch mode - continuously monitor for new files
watch_mode() {
    print_header "Bibliography Sync - Watch Mode"
    print_info "Monitoring: $SOURCE_DIR"
    print_info "Target: ${MAC_MINI_USER}@${MAC_MINI_IP}:${REMOTE_STAGING_DIR}"
    print_info "Press Ctrl+C to stop"
    echo ""

    log "Watch mode started"

    local last_count=0

    while true; do
        local current_count=$(find "$SOURCE_DIR" -name "*.pdf" -type f 2>/dev/null | wc -l | tr -d ' ')

        if [ "$current_count" -gt 0 ] && [ "$current_count" != "$last_count" ]; then
            echo ""
            print_info "Detected new files..."
            sync_files
            trigger_ingestion
            echo ""
            print_info "Waiting for new files... (checking every 30s)"
        fi

        last_count=$current_count
        sleep 30
    done
}

# One-time sync mode
oneshot_mode() {
    print_header "Bibliography Sync - One-time Sync"

    if ! check_source_directory; then
        exit 1
    fi

    if ! test_connection; then
        exit 1
    fi

    if ! setup_remote_directory; then
        exit 1
    fi

    sync_files
    trigger_ingestion

    print_success "Sync complete!"
}

# Main script
main() {
    case "${1:-oneshot}" in
        --watch|-w)
            if ! check_source_directory; then
                exit 1
            fi
            if ! test_connection; then
                exit 1
            fi
            if ! setup_remote_directory; then
                exit 1
            fi
            watch_mode
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Sync PDFs from MacBook DEVONthink export to Mac-mini"
            echo ""
            echo "Options:"
            echo "  --watch, -w     Watch mode - continuously monitor and sync"
            echo "  --help, -h      Show this help message"
            echo "  (no options)    One-time sync of current files"
            echo ""
            echo "Configuration:"
            echo "  Source:      $SOURCE_DIR"
            echo "  Destination: ${MAC_MINI_USER}@${MAC_MINI_IP}:${REMOTE_STAGING_DIR}"
            echo ""
            echo "Environment variables:"
            echo "  MAC_MINI_USER - Username on Mac-mini (default: drjforrest)"
            echo ""
            exit 0
            ;;
        *)
            oneshot_mode
            ;;
    esac
}

main "$@"
