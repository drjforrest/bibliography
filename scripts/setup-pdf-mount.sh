#!/bin/bash

# Setup SSHFS Mount for PDF Access
# This script runs ON THE PRODUCTION SERVER (mac-mini)
# It mounts the dev machine's PDF directory via SSHFS

set -e

echo "🔗 Setting up SSHFS mount for PDF access"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Configuration
DEV_USER="drjforrest"
DEV_HOST="MacBookM4.local"  # Update if needed
DEV_PDF_PATH="/Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/backend/data/pdfs"
MOUNT_POINT="/tmp/dev-pdfs"

# Check if SSHFS is installed
SSHFS_BIN="/usr/local/bin/sshfs"
if [ ! -f "$SSHFS_BIN" ]; then
    print_error "SSHFS not found at $SSHFS_BIN"
    print_error "Please install macfuse and sshfs manually."
    exit 1
fi

# Create mount point if it doesn't exist
if [ ! -d "$MOUNT_POINT" ]; then
    print_status "Creating mount point: $MOUNT_POINT"
    mkdir -p "$MOUNT_POINT"
fi

# Check if already mounted
if mount | grep -q "$MOUNT_POINT"; then
    print_warning "Mount point already in use. Unmounting..."
    umount "$MOUNT_POINT" 2>/dev/null || sudo umount "$MOUNT_POINT"
fi

# Test SSH connectivity to dev machine
print_status "Testing SSH connection to dev machine..."
if ! ssh -o ConnectTimeout=5 ${DEV_USER}@${DEV_HOST} "echo 'Connection successful'" &>/dev/null; then
    print_error "Cannot connect to dev machine at ${DEV_USER}@${DEV_HOST}"
    print_warning "Make sure:"
    print_warning "  1. Dev machine is powered on and connected to network"
    print_warning "  2. SSH is enabled on dev machine (System Settings > General > Sharing > Remote Login)"
    print_warning "  3. SSH keys are set up (run: ssh-copy-id ${DEV_USER}@${DEV_HOST})"
    print_warning "  4. Hostname is correct (you may need to use IP address instead)"
    exit 1
fi

print_status "SSH connection successful!"

# Mount via SSHFS
print_status "Mounting PDF directory from dev machine..."
$SSHFS_BIN ${DEV_USER}@${DEV_HOST}:${DEV_PDF_PATH} ${MOUNT_POINT} \
    -o follow_symlinks \
    -o auto_cache \
    -o reconnect \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=3

if [ $? -eq 0 ]; then
    print_status "✓ PDF directory mounted successfully!"
    print_status "Mount point: $MOUNT_POINT"
    print_status ""
    print_status "Testing mount..."
    if ls "$MOUNT_POINT" >/dev/null 2>&1; then
        print_status "✓ Mount is accessible"
        print_status ""
        print_status "To unmount: umount $MOUNT_POINT"
    else
        print_error "Mount succeeded but directory is not accessible"
        exit 1
    fi
else
    print_error "Failed to mount PDF directory"
    exit 1
fi

# Create launchd service for auto-mounting on boot (optional)
read -p "Do you want to create a LaunchAgent to auto-mount on startup? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    PLIST_PATH="$HOME/Library/LaunchAgents/com.hero-evidence-library.pdf-mount.plist"
    
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hero-evidence-library.pdf-mount</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/sshfs</string>
        <string>${DEV_USER}@${DEV_HOST}:${DEV_PDF_PATH}</string>
        <string>${MOUNT_POINT}</string>
        <string>-o</string>
        <string>follow_symlinks</string>
        <string>-o</string>
        <string>auto_cache</string>
        <string>-o</string>
        <string>reconnect</string>
        <string>-o</string>
        <string>ServerAliveInterval=15</string>
        <string>-o</string>
        <string>ServerAliveCountMax=3</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>NetworkState</key>
        <true/>
    </dict>
    <key>StandardErrorPath</key>
    <string>/tmp/pdf-mount-error.log</string>
    <key>StandardOutPath</key>
    <string>/tmp/pdf-mount.log</string>
</dict>
</plist>
EOF

    launchctl load "$PLIST_PATH"
    print_status "✓ LaunchAgent created and loaded"
    print_status "The PDF directory will auto-mount on startup"
fi

print_status ""
print_status "🎉 Setup complete!"
print_status "PDFs from dev machine are now accessible at: $MOUNT_POINT"
