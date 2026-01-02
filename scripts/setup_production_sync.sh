#!/bin/bash
# Setup Permanent DEVONthink Sync on Production
# This sets up a cron job to periodically sync DEVONthink database

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$HOME/production/hero-evidence-library"
SYNC_SCRIPT="$PROJECT_DIR/scripts/sync_production_devonthink.sh"
CRON_LOG="$PROJECT_DIR/logs/cron_sync.log"

echo -e "${BLUE}Setting up permanent DEVONthink sync on production${NC}"
echo ""

# Check if sync script exists
if [ ! -f "$SYNC_SCRIPT" ]; then
    echo -e "${YELLOW}Warning: Sync script not found at $SYNC_SCRIPT${NC}"
    echo "Please ensure the sync script is deployed to production first."
    exit 1
fi

# Make sync script executable
chmod +x "$SYNC_SCRIPT"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

echo -e "${BLUE}Setting up cron job...${NC}"

# Check if cron job already exists
CRON_EXISTS=$(crontab -l 2>/dev/null | grep -c "sync_production_devonthink.sh" || echo "0")

if [ "$CRON_EXISTS" -gt 0 ]; then
    echo -e "${YELLOW}Warning: Cron job already exists${NC}"
    echo "Current crontab entries:"
    crontab -l | grep "sync_production_devonthink.sh"
    echo ""
    read -p "Do you want to remove the existing entry and create a new one? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        crontab -l 2>/dev/null | grep -v "sync_production_devonthink.sh" | crontab -
    else
        echo "Keeping existing cron job."
        exit 0
    fi
fi

echo ""
echo -e "${BLUE}Choose sync frequency:${NC}"
echo "1. Daily at 2 AM (recommended)"
echo "2. Weekly (Sunday at 2 AM)"
echo "3. Manual only (no cron job)"
echo ""
read -p "Enter choice [1-3]: " FREQ_CHOICE

case $FREQ_CHOICE in
    1)
        CRON_SCHEDULE="0 2 * * *"
        DESCRIPTION="Daily at 2 AM"
        ;;
    2)
        CRON_SCHEDULE="0 2 * * 0"
        DESCRIPTION="Weekly on Sunday at 2 AM"
        ;;
    3)
        echo "Skipping cron job setup. You can run the sync manually with:"
        echo "  $SYNC_SCRIPT"
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $SYNC_SCRIPT >> $CRON_LOG 2>&1") | crontab -

echo ""
echo -e "${GREEN}✓ Cron job set up successfully!${NC}"
echo ""
echo "Schedule: $DESCRIPTION"
echo "Script: $SYNC_SCRIPT"
echo "Log file: $CRON_LOG"
echo ""
echo "View cron jobs with: crontab -l"
echo "Remove cron job with: crontab -e"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Test the sync script manually: $SYNC_SCRIPT"
echo "2. Monitor the first automated sync"
echo "3. Check logs at: $CRON_LOG"

