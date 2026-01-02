#!/bin/bash
# Quick deploy of just the migration CLI script to production
# Faster than full deploy when you only changed this one file

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}Quick Deploy: Migration CLI Script${NC}"
echo ""

# Test SSH connection
if ! ssh mac-mini "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${YELLOW}Error: Cannot connect to mac-mini${NC}"
    exit 1
fi

# Deploy the migration CLI script
echo -e "${BLUE}Deploying start_migration_cli.py...${NC}"
scp "$PROJECT_DIR/backend/start_migration_cli.py" mac-mini:~/production/hero-evidence-library/backend/ && \
    echo -e "${GREEN}✓ Deployed successfully${NC}" || \
    (echo -e "${YELLOW}✗ Deployment failed${NC}" && exit 1)

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Now try running the sync again on mac-mini:"
echo "  ./scripts/sync_production_devonthink.sh"

