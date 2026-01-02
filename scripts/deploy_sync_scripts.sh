#!/bin/bash
# Deploy DEVONthink Sync Scripts to Production
# Run this from your dev machine

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}Deploying DEVONthink Sync Scripts to Production${NC}"
echo ""

# Check if scripts exist
SYNC_SCRIPT="$SCRIPT_DIR/sync_production_devonthink.sh"
SETUP_SCRIPT="$SCRIPT_DIR/setup_production_sync.sh"
NUMPY_FIX_SCRIPT="$SCRIPT_DIR/fix_production_numpy.sh"

if [ ! -f "$SYNC_SCRIPT" ]; then
    echo -e "${YELLOW}Error: Sync script not found: $SYNC_SCRIPT${NC}"
    exit 1
fi

if [ ! -f "$SETUP_SCRIPT" ]; then
    echo -e "${YELLOW}Error: Setup script not found: $SETUP_SCRIPT${NC}"
    exit 1
fi

if [ ! -f "$NUMPY_FIX_SCRIPT" ]; then
    echo -e "${YELLOW}Warning: NumPy fix script not found: $NUMPY_FIX_SCRIPT${NC}"
    echo "It will not be deployed, but this is optional."
fi

# Test SSH connection
echo -e "${BLUE}Testing SSH connection to mac-mini...${NC}"
if ! ssh mac-mini "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${YELLOW}Error: Cannot connect to mac-mini${NC}"
    echo "Please ensure:"
    echo "  1. mac-mini is accessible"
    echo "  2. SSH keys are configured"
    echo "  3. SSH config has 'mac-mini' host alias"
    exit 1
fi

echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Deploy scripts
echo -e "${BLUE}Deploying scripts to production...${NC}"

scp "$SYNC_SCRIPT" mac-mini:~/production/hero-evidence-library/scripts/ && \
    echo -e "${GREEN}✓ Deployed sync_production_devonthink.sh${NC}" || \
    echo -e "${YELLOW}✗ Failed to deploy sync script${NC}"

scp "$SETUP_SCRIPT" mac-mini:~/production/hero-evidence-library/scripts/ && \
    echo -e "${GREEN}✓ Deployed setup_production_sync.sh${NC}" || \
    echo -e "${YELLOW}✗ Failed to deploy setup script${NC}"

if [ -f "$NUMPY_FIX_SCRIPT" ]; then
    scp "$NUMPY_FIX_SCRIPT" mac-mini:~/production/hero-evidence-library/scripts/ && \
        echo -e "${GREEN}✓ Deployed fix_production_numpy.sh${NC}" || \
        echo -e "${YELLOW}✗ Failed to deploy NumPy fix script${NC}"
fi

# Deploy install_uv.sh if it exists
INSTALL_UV_SCRIPT="$SCRIPT_DIR/install_uv.sh"
if [ -f "$INSTALL_UV_SCRIPT" ]; then
    scp "$INSTALL_UV_SCRIPT" mac-mini:~/production/hero-evidence-library/scripts/ && \
        echo -e "${GREEN}✓ Deployed install_uv.sh${NC}" || \
        echo -e "${YELLOW}✗ Failed to deploy install_uv.sh${NC}"
fi

echo ""

# Make scripts executable
echo -e "${BLUE}Making scripts executable on production...${NC}"
EXECUTABLE_SCRIPTS="~/production/hero-evidence-library/scripts/sync_production_devonthink.sh ~/production/hero-evidence-library/scripts/setup_production_sync.sh"
if [ -f "$NUMPY_FIX_SCRIPT" ]; then
    EXECUTABLE_SCRIPTS="$EXECUTABLE_SCRIPTS ~/production/hero-evidence-library/scripts/fix_production_numpy.sh"
fi
if [ -f "$INSTALL_UV_SCRIPT" ]; then
    EXECUTABLE_SCRIPTS="$EXECUTABLE_SCRIPTS ~/production/hero-evidence-library/scripts/install_uv.sh"
fi
ssh mac-mini "chmod +x $EXECUTABLE_SCRIPTS" && \
    echo -e "${GREEN}✓ Scripts are now executable${NC}" || \
    echo -e "${YELLOW}✗ Failed to make scripts executable${NC}"

# Create logs directory
echo -e "${BLUE}Creating logs directory...${NC}"
ssh mac-mini "mkdir -p ~/production/hero-evidence-library/logs" && \
    echo -e "${GREEN}✓ Logs directory ready${NC}" || \
    echo -e "${YELLOW}✗ Failed to create logs directory${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. (Optional) Install uv for faster package management:"
echo -e "   ${BLUE}ssh mac-mini${NC}"
echo -e "   ${BLUE}cd ~/production/hero-evidence-library${NC}"
echo -e "   ${BLUE}./scripts/install_uv.sh${NC}"
echo ""
echo "2. Fix NumPy compatibility issue (if needed):"
echo -e "   ${BLUE}./scripts/fix_production_numpy.sh${NC}"
echo ""
echo "3. SSH to mac-mini and run the initial sync:"
echo -e "   ${BLUE}ssh mac-mini${NC}"
echo -e "   ${BLUE}cd ~/production/hero-evidence-library${NC}"
echo -e "   ${BLUE}./scripts/sync_production_devonthink.sh${NC}"
echo ""
echo "4. After initial sync completes, set up automated syncs:"
echo -e "   ${BLUE}./scripts/setup_production_sync.sh${NC}"
echo ""
echo "5. Monitor progress:"
echo -e "   ${BLUE}tail -f ~/production/hero-evidence-library/logs/devonthink_sync.log${NC}"
echo ""

