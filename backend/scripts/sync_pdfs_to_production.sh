#!/bin/bash
# Sync PDFs from dev machine to production server
# This copies files to production's local storage (not SSHFS mount)

set -e

echo "📁 Syncing PDFs from dev machine to production"
echo "================================================"

# Configuration
PROD_USER="jforrest"
PROD_HOST="mac-mini"
PROD_PATH="~/production/hero-evidence-library/backend"
LOCAL_PDF_DIR="./backend/data/pdfs"
PROD_PDF_DIR="${PROD_PATH}/data/pdfs"

# Check if local PDF directory exists
if [ ! -d "$LOCAL_PDF_DIR" ]; then
    echo "❌ Local PDF directory not found: $LOCAL_PDF_DIR"
    exit 1
fi

echo "📊 Local PDFs: $(find $LOCAL_PDF_DIR -name '*.pdf' | wc -l | tr -d ' ') files"
echo ""

# Test connection
echo "🔍 Testing connection to production server..."
if ! ssh ${PROD_USER}@${PROD_HOST} "echo 'Connection successful'" 2>/dev/null; then
    echo "❌ Cannot connect to production server"
    echo "   Please ensure:"
    echo "   1. Tailscale is running"
    echo "   2. SSH access is configured"
    echo "   3. Production server is accessible"
    exit 1
fi

# Create production PDF directory
echo "📁 Creating production PDF directory..."
ssh ${PROD_USER}@${PROD_HOST} "mkdir -p ${PROD_PDF_DIR}"

# Sync files using rsync
echo "📤 Syncing PDFs to production..."
rsync -avz --progress \
    --exclude='*.tmp' \
    --exclude='*.lock' \
    "${LOCAL_PDF_DIR}/" \
    ${PROD_USER}@${PROD_HOST}:${PROD_PDF_DIR}/

echo ""
echo "✅ PDFs synced to production's local storage!"
echo ""
echo "📋 Production is now using local storage (independent of dev machine)"
echo ""
echo "Note: Production uses local storage now. SSHFS mount is no longer needed."
echo "To update production .env: PDF_STORAGE_ROOT=./data/pdfs"

