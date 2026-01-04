# Production PDF Storage Setup

## Problem

SSHFS mount from dev machine is not suitable for production because:
- Requires dev machine to always be running
- Network dependency
- Not reliable for production use

## Solution

Copy PDFs to production's local storage instead.

## Setup Steps

### 1. Update Production Environment

On production server, update `.env` to use local storage:

```bash
# SSH to production
ssh jforrest@mac-mini

# Edit production .env
cd ~/production/hero-evidence-library/backend
nano .env  # or use your preferred editor

# Update PDF_STORAGE_ROOT to use local storage:
PDF_STORAGE_ROOT=./data/pdfs

# Save and exit
```

### 2. Sync PDFs from Dev to Production

On your dev machine:

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library

# Run the sync script
./backend/scripts/sync_pdfs_to_production.sh
```

This will:
- Copy all PDFs from dev `backend/data/pdfs/` to production `backend/data/pdfs/`
- Use rsync for efficient transfer
- Preserve directory structure (YYYY/MM/)

### 3. Verify on Production

```bash
# SSH to production
ssh jforrest@mac-mini

cd ~/production/hero-evidence-library/backend

# Check files are there
ls -la data/pdfs/
find data/pdfs -name '*.pdf' | wc -l

# Verify database paths match
python scripts/move_export_pdfs_to_storage.py --dry-run
```

### 4. Restart Production Services

```bash
# On production
cd ~/production/hero-evidence-library

# Restart backend (adjust based on your service management)
# If using systemd/launchd, restart the service
# Or manually restart:
cd backend
# Stop existing process
pkill -f "uvicorn.*main:app.*8400" || true

# Start new process (or use your service manager)
nohup python main.py > ../hero_evidence_library_backend.log 2>&1 &
```

### 5. Ongoing Sync (Optional)

If you need to sync new files periodically, you can:

1. **Run sync script manually** when needed
2. **Set up cron job** on dev machine to sync periodically
3. **Use automated sync** - production will get files via MCP sync when you add new papers

## Storage Location

- **Dev**: `backend/data/pdfs/YYYY/MM/{uuid}.pdf`
- **Production**: `backend/data/pdfs/YYYY/MM/{uuid}.pdf` (local copy)

Both use the same structure, just separate copies.

