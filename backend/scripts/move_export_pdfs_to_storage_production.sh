#!/bin/bash
# Script to move PDFs from export folder to storage on production
# Run this on the production server (mac-mini)

set -e

echo "📁 Moving PDFs from export folder to storage on production"
echo "=========================================================="

# Navigate to backend directory
cd ~/production/hero-evidence-library/backend

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found in backend directory"
    echo "   Please ensure production environment is configured"
    exit 1
fi

# Check if export folder exists
EXPORT_DIR="$HOME/PDFs/Evidence_Library_Sync"
if [ ! -d "$EXPORT_DIR" ]; then
    echo "⚠️  Export folder not found: $EXPORT_DIR"
    echo "   This is normal if PDFs are accessed via SSHFS mount"
    exit 0
fi

# Run the Python script
echo "Running PDF move script..."
python scripts/move_export_pdfs_to_storage.py

echo ""
echo "✅ Done! Files should now be in the correct location"

