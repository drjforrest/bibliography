#!/bin/bash
# Setup SSH tunnel for PostgreSQL database connection
# Similar to SSHFS but for database connections (port forwarding)

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REMOTE_HOST="mac-mini"
REMOTE_PORT="5432"
LOCAL_PORT="5433"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info "Setting up SSH tunnel for PostgreSQL"
print_info "======================================"

# Check if tunnel is already running
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Port $LOCAL_PORT is already in use"
    read -p "Kill existing tunnel and create new one? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti:$LOCAL_PORT | xargs kill -9 2>/dev/null || true
        print_info "Killed existing process on port $LOCAL_PORT"
    else
        print_info "Using existing tunnel on port $LOCAL_PORT"
        exit 0
    fi
fi

# Test SSH connection
print_info "Testing SSH connection to $REMOTE_HOST..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes $REMOTE_HOST "echo 'SSH connection OK'" >/dev/null 2>&1; then
    print_error "Cannot connect to $REMOTE_HOST via SSH"
    print_error "Make sure SSH is configured and mac-mini is accessible"
    exit 1
fi

print_success "SSH connection OK"

# Create tunnel in background
print_info "Creating SSH tunnel: localhost:$LOCAL_PORT -> $REMOTE_HOST:$REMOTE_PORT"
ssh -f -N -L $LOCAL_PORT:localhost:$REMOTE_PORT $REMOTE_HOST

# Wait a moment for tunnel to establish
sleep 2

# Test tunnel
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_success "SSH tunnel established on port $LOCAL_PORT"
    print_info ""
    print_info "You can now use this DATABASE_URL:"
    echo -e "${GREEN}export DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:$LOCAL_PORT/hero_evidence_library_prod'${NC}"
    print_info ""
    print_info "To stop the tunnel, run:"
    echo -e "${YELLOW}lsof -ti:$LOCAL_PORT | xargs kill${NC}"
    print_info ""
    print_info "The tunnel is running in the background and will persist after closing this terminal"
    print_warning "The tunnel will close if the SSH connection is terminated or the remote host becomes unreachable"
else
    print_error "Failed to establish tunnel"
    exit 1
fi

