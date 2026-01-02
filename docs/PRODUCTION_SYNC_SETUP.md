# Production DEVONthink Sync Setup

## Overview

This guide sets up a **permanent, automated solution** for syncing papers from your DEVONthink BIBLIOGRAPHY database to the production server.

## Current Status

- **Production database**: 1,284 papers already imported (32% complete)
- **Remaining**: ~2,716 papers to import
- **Database**: BIBLIOGRAPHY
- **Status**: Sync tracking not initialized (needs MCP sync)

## Permanent Solution Architecture

### Two-Method Approach

1. **Initial Full Sync**: One-time complete migration of remaining ~2,716 records
2. **Ongoing Incremental Sync**: Automated periodic syncs to catch new papers

### Sync Methods

**Method 1: MCP Server Sync (Recommended)**
- Direct sync from DEVONthink via MCP server
- Creates proper sync tracking records
- Preserves folder hierarchy
- Best for ongoing operations

**Method 2: API Endpoint Sync**
- Uses FastAPI endpoints
- Can be triggered remotely
- Good for manual triggers

## Setup Instructions

### Step 1: Deploy Sync Scripts to Production

From your dev machine:

```bash
# Deploy the sync scripts
scp scripts/sync_production_devonthink.sh mac-mini:~/production/hero-evidence-library/scripts/
scp scripts/setup_production_sync.sh mac-mini:~/production/hero-evidence-library/scripts/
```

### Step 2: Run Initial Full Sync

SSH to mac-mini and run the initial sync:

```bash
ssh mac-mini
cd ~/production/hero-evidence-library
chmod +x scripts/sync_production_devonthink.sh
./scripts/sync_production_devonthink.sh
```

**Expected time**: 4-8 hours for ~2,716 records (depending on PDF sizes)

**What it does**:
- Connects to DEVONthink BIBLIOGRAPHY database via MCP
- Syncs all remaining papers
- Creates sync tracking records
- Generates embeddings for semantic search
- Creates thumbnails
- Logs everything to `~/production/hero-evidence-library/logs/devonthink_sync.log`

### Step 3: Set Up Automated Incremental Syncs

After the initial sync completes successfully:

```bash
ssh mac-mini
cd ~/production/hero-evidence-library
chmod +x scripts/setup_production_sync.sh
./scripts/setup_production_sync.sh
```

Choose your sync frequency:
- **Daily at 2 AM** (recommended for active use)
- **Weekly** (Sunday at 2 AM)
- **Manual only** (no cron job)

### Step 4: Monitor Syncs

Check sync status:

```bash
# View recent sync logs
ssh mac-mini "tail -f ~/production/hero-evidence-library/logs/devonthink_sync.log"

# View cron execution logs
ssh mac-mini "tail -f ~/production/hero-evidence-library/logs/cron_sync.log"

# Check current paper count
ssh mac-mini "/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -t -c 'SELECT COUNT(*) FROM scientific_papers WHERE dt_source_uuid IS NOT NULL;'"
```

## Manual Sync Options

### Option 1: Using Sync Script

```bash
ssh mac-mini
cd ~/production/hero-evidence-library
./scripts/sync_production_devonthink.sh
```

### Option 2: Using Migration CLI

```bash
ssh mac-mini
cd ~/production/hero-evidence-library
source backend/venv/bin/activate

# Get user ID first
python3 backend/scripts/check_import_status.py --production

# Run sync
python3 backend/start_migration_cli.py \
  --database "BIBLIOGRAPHY" \
  --user-id YOUR_USER_ID
```

### Option 3: Using API Endpoint

```bash
# Get auth token first
TOKEN=$(ssh mac-mini "curl -X POST http://localhost:8400/auth/login ...")

# Trigger sync
ssh mac-mini "curl -X POST http://localhost:8400/api/v1/devonthink/sync \
  -H 'Authorization: Bearer $TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{\"database_name\": \"BIBLIOGRAPHY\", \"search_space_id\": 1}'"
```

## Troubleshooting

### Sync Script Fails

**Check logs**:
```bash
ssh mac-mini "tail -50 ~/production/hero-evidence-library/logs/devonthink_sync.log"
```

**Common issues**:
1. **DEVONthink not running**: Ensure DEVONthink is open on your dev machine
2. **MCP server not configured**: Check MCP server is running
3. **Database connection**: Verify PostgreSQL is running
4. **User ID missing**: Run the script to see the error message

### Cron Job Not Running

**Check cron is set up**:
```bash
ssh mac-mini "crontab -l | grep sync_production"
```

**Check cron logs** (on mac-mini):
```bash
grep CRON /var/log/system.log | tail -20
```

**Test script manually**:
```bash
ssh mac-mini "~/production/hero-evidence-library/scripts/sync_production_devonthink.sh"
```

### Incremental Sync Issues

If incremental syncs are not working:

1. **Check DEVONthink sync status table**:
```bash
ssh mac-mini "/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -c 'SELECT COUNT(*), sync_status FROM devonthink_sync GROUP BY sync_status;'"
```

2. **Force resync if needed**:
```bash
ssh mac-mini "cd ~/production/hero-evidence-library && source backend/venv/bin/activate && python3 backend/start_migration_cli.py --database BIBLIOGRAPHY --user-id YOUR_USER_ID --force-resync"
```

## Monitoring & Maintenance

### Daily Health Check

Create a script to check sync status:

```bash
#!/bin/bash
# Check sync health
ssh mac-mini << 'EOF'
echo "=== DEVONthink Sync Status ==="
echo ""
echo "Last sync log:"
tail -5 ~/production/hero-evidence-library/logs/devonthink_sync.log
echo ""
echo "Paper count:"
/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -t -c 'SELECT COUNT(*) FROM scientific_papers WHERE dt_source_uuid IS NOT NULL;'
EOF
```

### Weekly Review

Check sync progress weekly:

```bash
# From your dev machine
cd backend
python scripts/check_import_status.py --production
```

This shows:
- Current paper count
- Progress toward 4000 records
- Any issues to address

## Expected Timeline

- **Initial full sync**: 4-8 hours for ~2,716 records
- **Incremental syncs**: 10-30 minutes (depends on new papers)
- **Daily sync**: Runs at 2 AM automatically
- **Total completion**: ~32% done, ~68% remaining

## Success Criteria

✅ Sync is successful when:
- All ~4000 papers are in the database
- `devonthink_sync` table has records tracking all papers
- Daily automated syncs are running
- Logs show successful syncs
- No errors in production logs

## Long-Term Maintenance

### Monthly Tasks

1. Review sync logs for any recurring errors
2. Check disk space (PDFs and embeddings use space)
3. Verify DEVONthink connection is working
4. Update sync scripts if needed

### When Adding New Papers to DEVONthink

- Papers will be automatically synced at the next scheduled sync
- Or trigger manual sync if needed immediately
- No action required - the system handles it automatically

## Next Steps After Setup

1. ✅ Run initial full sync (Step 2 above)
2. ✅ Set up automated syncs (Step 3 above)
3. ✅ Monitor first automated sync
4. ✅ Verify all ~4000 papers are imported
5. ✅ Celebrate! 🎉

---

**Last Updated**: 2025-01-20
**Status**: Production-ready permanent solution

