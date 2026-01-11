#!/bin/bash
#
# Cleanup script for expired visual abstracts
# This script runs the cleanup task to delete visual abstracts older than 30 days
#
# Usage:
#   ./cleanup_expired_visual_abstracts.sh
#

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Change to backend directory
cd "$BACKEND_DIR"

# Activate virtual environment if it exists
VENV_ACTIVATED=0
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    VENV_ACTIVATED=1
elif [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
    VENV_ACTIVATED=1
fi

if [ $VENV_ACTIVATED -eq 0 ]; then
    echo "Warning: No virtual environment found. Using system Python." >&2
    echo "This may fail if dependencies are not installed system-wide." >&2
fi

# Run the cleanup script
python -c "
import asyncio
import sys
sys.path.insert(0, '$BACKEND_DIR')
from app.tasks.cleanup_expired_abstracts import cleanup_expired_visual_abstracts

async def main():
    try:
        deleted_count = await cleanup_expired_visual_abstracts()
        print(f'✓ Cleanup completed: {deleted_count} expired visual abstracts deleted')
        return 0
    except Exception as e:
        print(f'✗ Cleanup failed: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

exit_code = asyncio.run(main())
sys.exit(exit_code)
"

# Log completion
echo "$(date): Visual abstracts cleanup completed"
