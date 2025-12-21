#!/bin/bash

# Secure Transfer Script for Database Schema Files to mac-mini
# This script securely transfers the bibliography database schema files and setup guide to the mac-mini
# using SCP over SSH with verification commands.

set -e  # Exit on any error

# Configuration variables
SSH_HOST="mac-mini"
DEST_DIR="/Users/jforrest/production/bibliography"

# Files to transfer
SCHEMA_FILES=(
    "create_bibliography_db.sql"
    "mac-mini-postgresql-setup-guide.md"
)

echo "Starting secure transfer of database schema files to mac-mini..."

# Create destination directory on remote host
echo "Creating destination directory on remote host..."
ssh "$SSH_USER@$SSH_HOST" "mkdir -p $DEST_DIR"

# Transfer files using SCP with progress display
echo "Transferring files..."
for file in "${SCHEMA_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Transferring $file..."
        scp -v "$file" "$SSH_USER@$SSH_HOST:$DEST_DIR/"
        echo "✓ Transferred $file"
    else
        echo "⚠ Warning: $file not found in current directory"
    fi
done

echo ""
echo "Transfer completed. Running verification..."

# Verification commands
echo "Verifying file integrity..."

# Check file existence and sizes
for file in "${SCHEMA_FILES[@]}"; do
    echo "Checking $file on remote host..."
    ssh "$SSH_USER@$SSH_HOST" "
        if [ -f '$DEST_DIR/$file' ]; then
            echo '✓ $file exists'
            echo '  Size:' \$(stat -f '%z bytes' '$DEST_DIR/$file' 2>/dev/null || stat -c '%s bytes' '$DEST_DIR/$file')
            echo '  Permissions:' \$(stat -c '%a' '$DEST_DIR/$file' 2>/dev/null || stat -f '%Lp' '$DEST_DIR/$file')
        else
            echo '✗ $file not found on remote host'
            exit 1
        fi
    "
done

# Compare file checksums for integrity verification
echo ""
echo "Verifying file integrity using checksums..."
for file in "${SCHEMA_FILES[@]}"; do
    if [ -f "$file" ]; then
        LOCAL_SHA=$(shasum -a 256 "$file" | awk '{print $1}')
        REMOTE_SHA=$(ssh "$SSH_USER@$SSH_HOST" "shasum -a 256 '$DEST_DIR/$file' 2>/dev/null | awk '{print \$1}' || echo 'failed'")

        if [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
            echo "✓ $file checksum verified (SHA256: ${LOCAL_SHA:0:16}...)"
        else
            echo "✗ $file checksum mismatch!"
            echo "  Local:  $LOCAL_SHA"
            echo "  Remote: $REMOTE_SHA"
            exit 1
        fi
    fi
done

# List transferred files
echo ""
echo "Summary of transferred files:"
ssh "$SSH_USER@$SSH_HOST" "
    echo 'Files in $DEST_DIR:'
    ls -la '$DEST_DIR'
    echo ''
    echo 'Total files:' \$(ls -1 '$DEST_DIR' | wc -l)
"

echo ""
echo "🎉 Transfer and verification completed successfully!"
echo ""
echo "Next steps:"
echo "1. On mac-mini, review the transferred files:"
echo "   ls -la $DEST_DIR"
echo "2. Follow the PostgreSQL setup guide:"
echo "   cat $DEST_DIR/mac-mini-postgresql-setup-guide.md"
echo "3. Execute the database schema creation:"
echo "   psql -d bibliography_db -f $DEST_DIR/create_bibliography_db.sql"