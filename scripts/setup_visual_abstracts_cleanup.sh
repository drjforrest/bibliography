#!/bin/bash
#
# Setup script for visual abstracts cleanup cron job
# This installs the launchd plist to run cleanup daily at 2 AM
#
# Usage:
#   ./setup_visual_abstracts_cleanup.sh
#

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="$SCRIPT_DIR/com.hero.visual_abstracts_cleanup.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_PLIST="$LAUNCHD_DIR/com.hero.visual_abstracts_cleanup.plist"

print_header "Setting up Visual Abstracts Cleanup Cron Job"

# Check if plist file exists
if [ ! -f "$PLIST_FILE" ]; then
    print_error "Plist file not found: $PLIST_FILE"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
if [ ! -d "$LAUNCHD_DIR" ]; then
    print_info "Creating LaunchAgents directory..."
    mkdir -p "$LAUNCHD_DIR"
    print_success "LaunchAgents directory created"
fi

# Check if already loaded
if launchctl list | grep -q "com.hero.visual_abstracts_cleanup"; then
    print_warning "Service is already loaded. Unloading first..."
    launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
print_info "Installing plist file..."
cp "$PLIST_FILE" "$LAUNCHD_PLIST"
print_success "Plist file installed to $LAUNCHD_PLIST"

# Load the service
print_info "Loading launchd service..."
launchctl load "$LAUNCHD_PLIST"

if [ $? -eq 0 ]; then
    print_success "Service loaded successfully"
else
    print_error "Failed to load service"
    exit 1
fi

# Verify it's loaded
if launchctl list | grep -q "com.hero.visual_abstracts_cleanup"; then
    print_success "Service is running and scheduled"
    print_info "Cleanup will run daily at 2:00 AM"
    print_info "Logs will be written to:"
    print_info "  - $HOME/.hero_visual_abstracts_cleanup.log"
    print_info "  - $HOME/.hero_visual_abstracts_cleanup_error.log"
else
    print_error "Service failed to load"
    exit 1
fi

print_header "Setup Complete"

echo ""
print_info "To manage the service:"
echo "  Start:   launchctl load $LAUNCHD_PLIST"
echo "  Stop:    launchctl unload $LAUNCHD_PLIST"
echo "  Restart: launchctl unload $LAUNCHD_PLIST && launchctl load $LAUNCHD_PLIST"
echo "  Status:  launchctl list | grep visual_abstracts_cleanup"
echo "  Logs:    tail -f $HOME/.hero_visual_abstracts_cleanup.log"
echo ""
