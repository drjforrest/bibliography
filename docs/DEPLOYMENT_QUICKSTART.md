# Quick Start: Deploy DEVONthink Sync

## Step 1: Deploy Scripts

From your dev machine, run:

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
./scripts/deploy_sync_scripts.sh
```

This will:
- ✅ Test SSH connection to mac-mini
- ✅ Copy sync scripts to production
- ✅ Make scripts executable
- ✅ Create logs directory

## Step 2: Run Initial Full Sync

SSH to mac-mini and start the sync:

```bash
ssh mac-mini
cd ~/production/hero-evidence-library
./scripts/sync_production_devonthink.sh
```

**This will take 4-8 hours** for ~2,716 remaining papers.

**What's happening:**
- Syncing papers from DEVONthink BIBLIOGRAPHY database
- Creating sync tracking records
- Generating embeddings for semantic search
- Creating thumbnails
- Logging everything to `~/production/hero-evidence-library/logs/devonthink_sync.log`

**Monitor progress:**
- Watch logs: `tail -f ~/production/hero-evidence-library/logs/devonthink_sync.log`
- Check from another terminal: `ssh mac-mini "tail -f ~/production/hero-evidence-library/logs/devonthink_sync.log"`

## Step 3: Set Up Automated Syncs

After initial sync completes, set up automated syncs:

```bash
# Still on mac-mini
./scripts/setup_production_sync.sh
```

Choose:
- **Daily at 2 AM** (recommended)
- **Weekly** (Sunday at 2 AM)
- **Manual only** (no cron job)

## Step 4: Verify Everything Works

Check final status:

```bash
# From your dev machine
cd backend
python scripts/check_import_status.py --production
```

You should see:
- ~4000 papers in database
- All from DEVONthink
- Sync tracking records created

## Troubleshooting

**If scripts aren't found:**
```bash
ssh mac-mini "ls -la ~/production/hero-evidence-library/scripts/*.sh"
```

**If sync fails:**
```bash
ssh mac-mini "tail -50 ~/production/hero-evidence-library/logs/devonthink_sync.log"
```

**Check if DEVONthink is accessible:**
- Ensure DEVONthink is running
- Ensure MCP server is configured
- Check backend logs on mac-mini

## That's It!

Once set up:
- ✅ All papers are synced
- ✅ New papers sync automatically
- ✅ Zero maintenance required

See `docs/PRODUCTION_SYNC_SETUP.md` for detailed documentation.

