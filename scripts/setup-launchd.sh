#!/bin/bash

# setup-launchd.sh
# Install and configure launchd service for automatic PDF ingestion on Mac-mini

set -e

PLIST_FILE="com.bibliography.ingestion.plist"
PLIST_SOURCE="$(cd "$(dirname "$0")" && pwd)/${PLIST_FILE}"
PLIST_DEST="${HOME}/Library/LaunchAgents/${PLIST_FILE}"

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

print_header "Bibliography Ingestion Service Setup"

# Check if plist source exists
if [ ! -f "$PLIST_SOURCE" ]; then
    print_error "Source plist file not found: $PLIST_SOURCE"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "${HOME}/Library/LaunchAgents"
print_success "LaunchAgents directory ready"

# Stop existing service if running
if launchctl list | grep -q "com.bibliography.ingestion"; then
    print_info "Stopping existing service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    print_success "Existing service stopped"
fi

# Copy plist file
print_info "Installing service configuration..."
cp "$PLIST_SOURCE" "$PLIST_DEST"
print_success "Configuration installed to $PLIST_DEST"

# Load the service
print_info "Loading service..."
if launchctl load "$PLIST_DEST"; then
    print_success "Service loaded successfully"
else
    print_error "Failed to load service"
    exit 1
fi

# Check service status
sleep 2
if launchctl list | grep -q "com.bibliography.ingestion"; then
    print_success "Service is running"
else
    print_warning "Service loaded but not running. Check logs:"
    print_info "  stdout: ${HOME}/.bibliography_ingestion_stdout.log"
    print_info "  stderr: ${HOME}/.bibliography_ingestion_stderr.log"
fi

echo ""
print_header "Service Management Commands"
echo ""
echo "Start service:"
echo "  launchctl load ${PLIST_DEST}"
echo ""
echo "Stop service:"
echo "  launchctl unload ${PLIST_DEST}"
echo ""
echo "Restart service:"
echo "  launchctl unload ${PLIST_DEST} && launchctl load ${PLIST_DEST}"
echo ""
echo "View service status:"
echo "  launchctl list | grep com.bibliography.ingestion"
echo ""
echo "View logs:"
echo "  tail -f ${HOME}/.bibliography_ingestion_stdout.log"
echo "  tail -f ${HOME}/.bibliography_ingestion_stderr.log"
echo ""

print_success "Setup complete!"
