# Syncing DEVONthink from MacBook to Production

## The Problem

DEVONthink is running on your MacBook, but the production server (mac-mini) can't access it because:

- DEVONthink MCP server needs to connect locally to DEVONthink
- Running the sync on mac-mini means it tries to find DEVONthink on mac-mini (which doesn't exist)

## The Solution

Run the sync **from your MacBook** (where DEVONthink is running), but point it to the **production database**.

## Quick Setup

### Step 1: Update .env to Point to Production

Edit `backend/.env` on your MacBook to point to production database:

```bash
# In backend/.env on your MacBook
DATABASE_URL=postgresql+asyncpg://USERNAME:PASSWORD@mac-mini:5432/hero_evidence_library_prod
```

Or if mac-mini isn't accessible by hostname, use the IP:

```bash
DATABASE_URL=postgresql+asyncpg://USERNAME:PASSWORD@192.168.1.69:5432/hero_evidence_library_prod
```

### Step 2: Make Sure PostgreSQL is Accessible

On mac-mini, ensure PostgreSQL allows connections from your MacBook:

```bash
# On mac-mini, edit postgresql.conf
# Find: listen_addresses = 'localhost'
# Change to: listen_addresses = '*'

# Edit pg_hba.conf, add:
host    all             all             192.168.1.0/24          md5

# Restart PostgreSQL
brew services restart postgresql@17
```

### Step 3: Run Sync from MacBook

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
chmod +x scripts/sync_from_macbook.sh
./scripts/sync_from_macbook.sh
```

## What This Does

- ✅ Runs on MacBook where DEVONthink is accessible
- ✅ Connects to production database on mac-mini
- ✅ Syncs all papers to production
- ✅ Logs everything for monitoring

## Alternative: Use SSH Tunnel for Database

If PostgreSQL isn't directly accessible, use SSH tunnel:

```bash
# Terminal 1: Create SSH tunnel
ssh -L 5433:localhost:5432 mac-mini

# Terminal 2: Run sync with tunneled database
export DATABASE_URL="postgresql+asyncpg://USERNAME:PASSWORD@localhost:5433/hero_evidence_library_prod"
./scripts/sync_from_macbook.sh
```

## Monitoring

Watch the sync progress:

```bash
tail -f logs/devonthink_sync_macbook.log
```

The sync will take several hours for ~2700 records. To run it in the background and allow closing your terminal:
