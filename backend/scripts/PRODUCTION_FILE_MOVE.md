# Moving PDFs to Storage on Production

## Overview

Since production uses SSHFS mount from your dev machine, files moved on dev should already be accessible on production. However, if production database has missing file references, you may need to verify.

## Quick Check

On production server (mac-mini):

```bash
# SSH to production
ssh jforrest@mac-mini

# Navigate to project
cd ~/production/hero-evidence-library/backend

# Check if SSHFS mount is working
ls /tmp/dev-pdfs

# Check file status in production database
python scripts/move_export_pdfs_to_storage.py --dry-run
```

## If SSHFS Mount is Active

If `/tmp/dev-pdfs` is mounted and shows your files, then production should already see them! The files we moved on dev are automatically accessible on production.

## If Production Database Has Different Files

If production database has its own file references that need fixing:

1. **Ensure SSHFS mount is active**:

   ```bash
   # On production
   mount | grep /tmp/dev-pdfs
   ```

2. **If mount is missing, set it up**:

   ```bash
   # Run the mount setup script
   ./scripts/setup-pdf-mount.sh
   ```

3. **Run the move script** (if production has its own export folder):
   ```bash
   # On production
   cd ~/production/hero-evidence-library/backend
   python scripts/move_export_pdfs_to_storage.py
   ```

## Note

Since production uses SSHFS mount from dev machine:

- Files moved on dev → automatically available on production (if mount is active)
- Production database file paths should match dev database file paths
- No need to copy files to production - they're accessed remotely via SSHFS
