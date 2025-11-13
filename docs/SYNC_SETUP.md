# Bibliography MacBook → Mac-mini Sync Setup

This guide explains how to set up automated PDF syncing from your MacBook (where DEVONthink runs) to your Mac-mini (where PostgreSQL runs).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ MacBook (Source)                                                    │
│                                                                     │
│  DEVONthink "Reference" DB                                         │
│         ↓                                                           │
│  Export to ~/Desktop/devonthink_export/                            │
│         ↓                                                           │
│  sync-to-macmini.sh (watches & transfers via SSH/rsync)           │
│         ↓                                                           │
│  ========== Tailscale VPN (100.75.201.24) ==========              │
│         ↓                                                           │
└─────────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Mac-mini (Deployment)                                               │
│                                                                     │
│  ~/dev/devprojects/bibliography/data/incoming/                     │
│         ↓                                                           │
│  ingest-from-macbook.sh (watches & processes)                      │
│         ↓                                                           │
│  FastAPI Backend → PostgreSQL + pgvector                           │
│         ↓                                                           │
│  UUID-based storage in ./data/pdfs/YYYY/MM/                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### On Both Machines

1. **Tailscale** installed and running
   - Your Mac-mini should be accessible at `100.75.201.24`

2. **SSH configured** between machines
   - You mentioned SSH keys are already set up ✓

### On MacBook

1. DEVONthink with "Reference" database
2. Export destination: `~/PDFs/Evidence_Library_Sync/`
3. AppleScript Smart Rule configured to export PDFs and metadata CSV

### On Mac-mini

1. PostgreSQL with pgvector extension
2. Bibliography backend installed and configured
3. Python virtual environment set up in `backend/venv/`

---

## Setup Instructions

### Step 1: Initial Setup on Mac-mini

SSH into your Mac-mini and run these commands:

```bash
# Navigate to project directory
cd ~/dev/devprojects/bibliography

# Ensure the incoming directory exists
mkdir -p data/incoming

# Test the backend
cd backend
source venv/bin/activate
python main.py --reload

# In another terminal, test the health endpoint
curl http://localhost:8000/api/v1/health
```

### Step 2: Set Up Auto-Ingestion Service on Mac-mini

This creates a background service that automatically processes incoming PDFs:

```bash
cd ~/dev/devprojects/bibliography

# Install the launchd service
./scripts/setup-launchd.sh

# Verify it's running
launchctl list | grep com.bibliography.ingestion

# Check logs
tail -f ~/.bibliography_ingestion_stdout.log
```

The service will:
- Automatically start on boot
- Monitor `~/dev/devprojects/bibliography/data/incoming/` for new PDFs
- Process them into the bibliography system
- Restart automatically if it crashes

### Step 3: Configure MacBook Sync Script

On your MacBook, verify the export directory exists:

```bash
# Create export directory if needed
mkdir -p ~/PDFs/Evidence_Library_Sync

# Test connection to Mac-mini
ssh drjforrest@100.75.201.24 "echo 'Connection successful'"
```

### Step 4: Export PDFs from DEVONthink Using Smart Rule

Your AppleScript Smart Rule exports both PDFs and metadata to `~/PDFs/Evidence_Library_Sync/`.

**What it exports:**
- PDFs with UUID-based filenames (e.g., `abc123-uuid.pdf`)
- `active_library.csv` with metadata (name, description, labels, comments, paths)

**To run the export:**
1. In DEVONthink, select records you want to sync
2. Trigger your Smart Rule (or it runs automatically based on your rule settings)
3. Files appear in `~/PDFs/Evidence_Library_Sync/`

The CSV file contains rich metadata that will be preserved during import, including:
- DEVONthink UUID (for tracking)
- Name and description
- Record labels (colors)
- Finder comments
- Original file paths

---

## Usage

### One-Time Sync (MacBook)

Transfer current files in the export folder:

```bash
cd ~/dev/devprojects/bibliography
./scripts/sync-to-macmini.sh
```

This will:
1. Check connection to Mac-mini
2. Transfer all PDFs via rsync
3. Trigger ingestion on Mac-mini
4. Remove source files after successful transfer

### Watch Mode (MacBook)

Continuously monitor and sync new files:

```bash
cd ~/dev/devprojects/bibliography
./scripts/sync-to-macmini.sh --watch
```

This runs in the foreground and will:
- Check for new PDFs every 30 seconds
- Automatically transfer and trigger ingestion
- Show progress in real-time

Press `Ctrl+C` to stop.

### Running as Background Service (MacBook)

To run the sync script in the background:

```bash
# Start in background
nohup ./scripts/sync-to-macmini.sh --watch > ~/.bibliography_sync.log 2>&1 &

# Check if running
ps aux | grep sync-to-macmini

# View logs
tail -f ~/.bibliography_sync.log

# Stop (find PID first)
kill <PID>
```

---

## Workflow Examples

### Workflow 1: Manual Batch Export

**On MacBook:**
1. Select papers in DEVONthink and run your Smart Rule
2. PDFs + CSV are exported to `~/PDFs/Evidence_Library_Sync/`
3. Run: `./scripts/sync-to-macmini.sh`
4. Files transfer and are automatically processed

**On Mac-mini:**
- Ingestion service (already running) automatically processes both PDFs and CSV metadata
- Check logs: `tail -f ~/.bibliography_ingestion_stdout.log`

**Benefits of CSV metadata:**
- Preserves DEVONthink labels and comments
- Maintains single-sentence descriptions
- Enables duplicate detection via UUID tracking
- Faster than re-extracting all metadata from PDFs

### Workflow 2: Continuous Sync

**On MacBook:**
1. Start watch mode: `./scripts/sync-to-macmini.sh --watch`
2. Leave it running (or run in background with nohup)

**As you work:**
1. Export PDFs from DEVONthink whenever needed
2. Sync script automatically detects and transfers them
3. Mac-mini ingestion service automatically processes them

### Workflow 3: Scheduled Sync

**On MacBook**, create a launchd plist similar to Mac-mini's:

```bash
# Create scheduled sync (example: every hour)
# Edit: ~/Library/LaunchAgents/com.bibliography.sync.plist
```

---

## File Organization on Mac-mini

After ingestion, files are organized as:

```
~/dev/devprojects/bibliography/
├── data/
│   ├── incoming/              # Staging area (temporary)
│   ├── pdfs/                  # Permanent storage
│   │   ├── 2025/
│   │   │   ├── 01/
│   │   │   │   ├── <uuid-1>.pdf
│   │   │   │   └── <uuid-2>.pdf
│   │   │   └── 02/
│   │   │       └── <uuid-3>.pdf
│   └── watched/               # Alternative ingestion method
└── backend/
    └── ...
```

Each PDF is:
1. Assigned a UUID
2. Stored in `data/pdfs/YYYY/MM/<uuid>.pdf`
3. Indexed in PostgreSQL with metadata
4. Vectorized for semantic search
5. SHA256 hashed to prevent duplicates

---

## Monitoring and Troubleshooting

### Check Sync Status

**On MacBook:**
```bash
# View sync log
tail -f ~/.bibliography_sync.log

# Check export directory
ls -lh ~/PDFs/Evidence_Library_Sync/

# Check CSV contents
head ~/PDFs/Evidence_Library_Sync/active_library.csv
```

**On Mac-mini:**
```bash
# View ingestion logs
tail -f ~/.bibliography_ingestion_stdout.log
tail -f ~/.bibliography_ingestion_stderr.log

# Check incoming directory
ls -lh ~/dev/devprojects/bibliography/data/incoming/

# Check database
psql bibliography_db -c "SELECT COUNT(*) FROM scientific_papers;"
```

### Common Issues

#### Issue: "Cannot connect to Mac-mini"

**Solutions:**
1. Ensure Tailscale is running on both machines
2. Check IP address: `tailscale ip`
3. Test SSH: `ssh drjforrest@100.75.201.24`
4. Verify SSH is enabled on Mac-mini: System Settings → Sharing → Remote Login

#### Issue: "Backend not running on Mac-mini"

**Solutions:**
```bash
# On Mac-mini, manually start backend
cd ~/dev/devprojects/bibliography/backend
source venv/bin/activate
python main.py --reload

# Or restart ingestion service
launchctl unload ~/Library/LaunchAgents/com.bibliography.ingestion.plist
launchctl load ~/Library/LaunchAgents/com.bibliography.ingestion.plist
```

#### Issue: "Files stuck in incoming directory"

**Solutions:**
```bash
# On Mac-mini, manually trigger ingestion
cd ~/dev/devprojects/bibliography
./scripts/ingest-from-macbook.sh

# Or restart the service
launchctl unload ~/Library/LaunchAgents/com.bibliography.ingestion.plist
launchctl load ~/Library/LaunchAgents/com.bibliography.ingestion.plist
```

#### Issue: "Duplicate files"

The system automatically handles duplicates via SHA256 hashing. If a PDF with the same content already exists, it won't be re-stored.

---

## Advanced Configuration

### Change Mac-mini IP/Hostname

Edit `scripts/sync-to-macmini.sh`:

```bash
MAC_MINI_IP="<new-ip-address>"
```

### Use Different Export Directory

Edit `scripts/sync-to-macmini.sh`:

```bash
SOURCE_DIR="${HOME}/Documents/MyExports"
```

### Change Sync Interval

For watch mode, edit the `sleep` duration in `scripts/sync-to-macmini.sh`:

```bash
sleep 30  # Change to desired seconds
```

### Use Shared Folder Instead of SSH

If you prefer a shared network folder:

1. Set up SMB share on Mac-mini pointing to `~/dev/devprojects/bibliography/data/incoming/`
2. Mount it on MacBook: `mount_smbfs //drjforrest@100.75.201.24/incoming ~/Desktop/macmini_incoming`
3. Export PDFs directly to the mounted folder
4. Mac-mini ingestion service will pick them up automatically

---

## Production Deployment Notes

Since your Mac-mini is the deployment environment:

1. **Backend should run as a service** (not just development mode)
   - Consider using systemd/launchd for the FastAPI backend
   - Use a production WSGI server like uvicorn with proper workers

2. **Database backups** should be automated:
   ```bash
   # Add to crontab
   0 2 * * * pg_dump bibliography_db > ~/backups/bibliography_$(date +\%Y\%m\%d).sql
   ```

3. **Log rotation** for the ingestion service:
   ```bash
   # Create /etc/newsyslog.d/bibliography.conf
   ~/.bibliography_*.log    644  7    100  *    GZ
   ```

4. **Monitoring** - consider adding:
   - Disk space monitoring for `data/pdfs/`
   - Database connection health checks
   - Alert if ingestion service stops

---

## Service Management

### Mac-mini Ingestion Service

```bash
# Start
launchctl load ~/Library/LaunchAgents/com.bibliography.ingestion.plist

# Stop
launchctl unload ~/Library/LaunchAgents/com.bibliography.ingestion.plist

# Restart
launchctl unload ~/Library/LaunchAgents/com.bibliography.ingestion.plist && \
launchctl load ~/Library/LaunchAgents/com.bibliography.ingestion.plist

# View status
launchctl list | grep com.bibliography.ingestion

# View logs
tail -f ~/.bibliography_ingestion_stdout.log
tail -f ~/.bibliography_ingestion_stderr.log

# Disable (won't start on boot)
launchctl unload ~/Library/LaunchAgents/com.bibliography.ingestion.plist
rm ~/Library/LaunchAgents/com.bibliography.ingestion.plist
```

---

## Quick Reference

### MacBook Commands

| Command | Purpose |
|---------|---------|
| `./scripts/sync-to-macmini.sh` | One-time sync |
| `./scripts/sync-to-macmini.sh --watch` | Continuous sync |
| `tail -f ~/.bibliography_sync.log` | View sync logs |

### Mac-mini Commands

| Command | Purpose |
|---------|---------|
| `./scripts/ingest-from-macbook.sh` | Manual ingestion |
| `./scripts/setup-launchd.sh` | Install auto-ingestion service |
| `tail -f ~/.bibliography_ingestion_stdout.log` | View ingestion logs |
| `launchctl list \| grep bibliography` | Check service status |

---

## Next Steps

1. **Test the setup:**
   ```bash
   # On MacBook: Export a single PDF to test
   # Then run:
   ./scripts/sync-to-macmini.sh
   ```

2. **Verify on Mac-mini:**
   ```bash
   # Check if file was processed
   tail -20 ~/.bibliography_ingestion_stdout.log

   # Check database
   psql bibliography_db -c "SELECT title, file_path FROM scientific_papers ORDER BY created_at DESC LIMIT 5;"
   ```

3. **Set up continuous sync** on MacBook if needed

4. **Configure production deployment** for Mac-mini backend

---

## Support

For issues or questions:
- Check logs first (both MacBook and Mac-mini)
- Verify Tailscale connection: `ping 100.75.201.24`
- Ensure both scripts are executable: `chmod +x scripts/*.sh`
- Check file permissions on staging directories
