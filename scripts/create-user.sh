#!/bin/bash

# Create a test user via API

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

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

echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}  👤 Create User${NC}"
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    print_error "Backend is not running on http://localhost:8000"
    print_info "Start it with: ./dev.sh --backend"
    exit 1
fi

# Get user details
read -p "Email: " EMAIL
read -sp "Password: " PASSWORD
echo ""

print_info "Creating user..."

RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

if echo "$RESPONSE" | grep -q "error\|detail"; then
    print_error "Failed to create user"
    echo "$RESPONSE"
    exit 1
else
    print_success "User created successfully!"
    echo ""
    print_info "You can now login at http://localhost:3000/auth/login"
    echo "  Email: $EMAIL"
fi
