# Next Steps: PDF Data Transfer Status

## Current Status Summary

Based on the codebase review, here's what has been completed and what remains:

### ✅ What's Been Done

1. **Infrastructure is Ready**

   - Database schema with all necessary tables
   - DEVONthink sync service implemented
   - CSV import script created (`import_from_devonthink_csv.py`)
   - MCP server integration for direct DEVONthink sync
   - File storage system with UUID-based naming
   - Thumbnail generation working
   - Vectorization pipeline for semantic search

2. **Test Migration Completed**
   - Test syncs completed (small batches)
   - System verified working end-to-end
   - Production database exists: `hero_evidence_library_prod`

### ⚠️ What's NOT Completed

**PDF Data Transfer Status: NEEDS VERIFICATION**

1. **Total DEVONthink Records**: ~**4000 records** in DEVONthink database
2. **CSV File**: Has **5288 lines** (header + records, some may be duplicates or include metadata)
3. **Production Database**: Needs to be checked - many records may already be there
4. **Local Database**: Status unknown - needs verification

**⚠️ IMPORTANT**: Check production database first! Many records may already be imported there.

## First: Check Current Status

**Before doing anything, check what's already imported:**

### Check Production Database (Most Important)

```bash
cd backend
python scripts/check_import_status.py --production
```

Or manually via SSH:

```bash
ssh <your-mac-hostname> "/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -c 'SELECT COUNT(*) FROM scientific_papers WHERE dt_source_uuid IS NOT NULL;'"
```

### Check Local Development Database

```bash
cd backend
python scripts/check_import_status.py
```

### Check Both

```bash
cd backend
python scripts/check_import_status.py --both
```

This will show you:

- How many papers are in each database
- How many are from DEVONthink
- What still needs to be imported

---

## Next Steps - Choose Your Method

Based on the status check, choose one of these methods:

---

## Method 1: Complete CSV Import (Recommended - Simpler)

**Best for**: You have the CSV file ready and want full control

### Prerequisites

- CSV file at: `~/PDFs/Evidence_Library_Sync/active_library.csv` (or `/data/thumbnail_index.csv`)
- PDF files in: `~/PDFs/Evidence_Library_Sync/{uuid}.pdf`
- Your user ID from the database

### Steps to Complete CSV Import

1. **Get Your User ID**:

```bash
cd backend
python -c "
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from app.db import User
from app.config import config

async def get_user():
    engine = create_async_engine(config.DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(select(User))
        users = result.fetchall()
        for user in users:
            print(f'Email: {user.email}, ID: {user.id}')
    await engine.dispose()

asyncio.run(get_user())
"
```

2. **Import All Remaining Records**:

```bash
cd backend
python scripts/import_from_devonthink_csv.py \
  --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
  --user-id YOUR_USER_ID_HERE
```

Or if using the data directory:

```bash
python scripts/import_from_devonthink_csv.py \
  --csv ../../data/thumbnail_index.csv \
  --user-id YOUR_USER_ID_HERE
```

**Expected**: Imports remaining records from CSV, processes PDFs, generates thumbnails, creates embeddings

**Time Estimate**: Varies based on how many records remain (the CSV has ~5288 lines total)

---

## Method 2: Full DEVONthink MCP Sync (Advanced)

**Best for**: You want to sync your entire DEVONthink database directly

### Prerequisites

- DEVONthink running on your Mac
- MCP server configured (`npx -y mcp-server-devonthink`)
- Redis running (for progress tracking)
- Your user ID from the database

### Steps to Complete Full Sync

1. **Start the Migration**:

```bash
cd backend
python start_migration_cli.py \
  --database "BIBLIOGRAPHY" \
  --user-id YOUR_USER_ID_HERE
```

Or use the enhanced migration service:

```bash
python start_migration_cli.py \
  --database "BIBLIOGRAPHY" \
  --user-id YOUR_USER_ID_HERE \
  --folder "/Your/Folder/Path"  # Optional: sync specific folder
```

2. **Monitor Progress**:
   The script will show progress. To check status later:

```bash
python start_migration_cli.py \
  --status migration_BIBLIOGRAPHY_YOUR_USER_ID_TIMESTAMP
```

**Expected**: Syncs all ~4000 PDF records from DEVONthink, preserves folder hierarchy

**Time Estimate**: 4-8 hours for ~4000 records (depending on PDF sizes and network speed)

---

## Verify Completion

After either method, verify the import:

```bash
cd backend
python start_simple_migration.py --status
```

Or check via API:

```bash
curl http://localhost:8000/api/v1/papers/?limit=10 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Recommendations

1. **Start with CSV Method** (if you have the CSV ready):

   - Faster setup
   - More control over what gets imported
   - Easier to troubleshoot
   - Complete the remaining 240 records

2. **Then Use MCP Sync** (for full database):
   - Sync everything from DEVONthink
   - Preserves folder structure
   - Handles incremental updates automatically

---

## Files to Check

- CSV location: `~/PDFs/Evidence_Library_Sync/active_library.csv` or `/data/thumbnail_index.csv`
- Import script: `backend/scripts/import_from_devonthink_csv.py`
- Migration CLI: `backend/start_migration_cli.py`
- Sync service: `backend/app/services/devonthink_sync_service.py`

---

## Troubleshooting

### If CSV Import Fails:

- Check CSV file exists and is readable
- Verify PDF files exist at paths specified in CSV
- Ensure user ID is correct
- Check database connection in `.env`

### If MCP Sync Fails:

- Verify DEVONthink is running
- Check MCP server is configured correctly
- Ensure Redis is running (for progress tracking)
- Check database name matches your DEVONthink database

### Permission Errors:

- Make sure backend directory has write permissions
- Check PDF storage directory is writable: `data/pdfs/`

---

## Summary

**Current Situation**:

- **Total DEVONthink records**: ~4000 papers
- **CSV file**: 5288 lines (may include duplicates or metadata rows)
- **Production database**: Status unknown - **needs to be checked first!**
- **Local database**: Status unknown - needs verification

**Action Required**:

1. **FIRST**: Check production database status using the status check script
2. **THEN**: Determine what's missing and choose appropriate import method
3. **FINALLY**: Complete the transfer of remaining PDFs

**Important**: Many records may already be on the production server. Always check status before importing!
