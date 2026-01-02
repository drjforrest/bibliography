# Quick Sync Instructions

## Problem
DEVONthink is on your MacBook, but production server can't access it.

## Solution
Run sync from MacBook, connect to production database.

## Steps

### Option 1: Direct Database Connection (if accessible)

```bash
# On your MacBook
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library

# Set production database URL
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@mac-mini:5432/hero_evidence_library_prod"

# Run sync
./scripts/sync_from_macbook.sh
```

### Option 2: SSH Tunnel (if database not directly accessible)

```bash
# Terminal 1: Create SSH tunnel to production database
ssh -L 5433:localhost:5432 mac-mini

# Terminal 2: Run sync with tunneled database
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/hero_evidence_library_prod"
./scripts/sync_from_macbook.sh
```

## What Happens

1. ✅ Checks DEVONthink is running (on MacBook)
2. ✅ Connects to production database (mac-mini)
3. ✅ Syncs ~2700 remaining papers
4. ✅ Takes 4-8 hours
5. ✅ Logs everything to `logs/devonthink_sync_macbook.log`

## Monitor Progress

```bash
tail -f logs/devonthink_sync_macbook.log
```

## Verify After Sync

```bash
cd backend
python scripts/check_import_status.py --production
```

You should see ~4000 papers total after sync completes.

