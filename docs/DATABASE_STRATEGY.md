# v2.0 Database Integration Plan - Shared Database Strategy

## Decision: Shared Database with Additive Migrations ✅

Both v1 and v2 will use the same PostgreSQL database with v2 adding new tables via Alembic.

---

## Safety Rules

### ✅ ALLOWED in v2 Migrations:
- Create new tables (`podcasts`, `summaries`, etc.)
- Add new columns to NEW tables
- Create new indexes on NEW tables
- Add new relationships/foreign keys to NEW tables

### ❌ FORBIDDEN in v2 Migrations:
- Modify existing v1 tables
- Drop existing columns
- Rename existing tables
- Change existing column types
- Alter existing indexes on v1 tables

**Enforcement**: We'll add a migration check script to verify these rules.

---

## Step-by-Step Implementation

### Step 1: Integrate v2 Models into Main db.py

```bash
# In v2 repo
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend/app
```

**Tasks**:
1. Copy v2 model definitions from `v2_models.py` into `db.py`
2. Add relationships to existing models (User, SearchSpace)
3. Import SummaryType enum in db.py
4. Remove `v2_models.py` (consolidated into db.py)

### Step 2: Create Alembic Migration

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend

# Generate migration
alembic revision --autogenerate -m "Add v2.0 content generation tables (podcasts, summaries, infographics, slide_decks)"

# Review the generated migration file
# Check alembic/versions/xxxx_add_v2_0_content.py
```

**What the migration will create**:
- `podcasts` table with columns and indexes
- `summaries` table with SummaryType enum
- `infographics` table
- `slide_decks` table
- Foreign key constraints to `users` and `searchspaces`
- Relationships are handled by SQLAlchemy (not DB-level)

### Step 3: Test Migration (Safely)

```bash
# Option A: Test on local dev database
# Your local DB is separate from Mac Mini production, so safe

# Check current migration state
alembic current

# Preview what will happen (don't apply)
alembic upgrade head --sql > migration_preview.sql
# Review migration_preview.sql

# Apply migration
alembic upgrade head

# Verify tables created
psql -d hero_evidence_library -c "\dt"
# Should show new tables: podcasts, summaries, infographics, slide_decks
```

### Step 4: Verify v1 Still Works

```bash
# Start v1 app
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/backend
uvicorn main:app --reload --port 8000

# Test key endpoints
curl http://localhost:8000/api/papers
curl http://localhost:8000/api/search-spaces
# Should work normally - v1 ignores new tables
```

### Step 5: Verify v2 Can Access Everything

```bash
# Start v2 app
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend
uvicorn main:app --reload --port 8001

# In Python shell or test script
from app.db import get_async_session, Podcast, ScientificPaper

# Should be able to query both v1 and v2 tables
papers = session.execute(select(ScientificPaper)).scalars().all()
podcasts = session.execute(select(Podcast)).scalars().all()
```

---

## Database Configuration

### Connection Settings (Same for Both)

Both v1 and v2 use the same DATABASE_URL:

```bash
# backend/.env (in both repos)
DATABASE_URL=postgresql+asyncpg://username:password@localhost/hero_evidence_library
```

If you're using the Mac Mini for production:
```bash
# Production (Mac Mini)
DATABASE_URL=postgresql+asyncpg://username:password@macmini.local/hero_evidence_library

# Development (MacBook)
DATABASE_URL=postgresql+asyncpg://username:password@localhost/hero_evidence_library
```

---

## Migration Version Control

### Alembic Versions Directory

```
backend/alembic/versions/
├── abc123_initial_schema.py          # v1 migrations
├── def456_add_papers.py
├── ghi789_add_tags.py
└── jkl012_add_v2_podcasts.py         # ← New v2 migration
```

**Important**: When v2 creates a migration, the version file must be committed to git:

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# After running: alembic revision --autogenerate
git add backend/alembic/versions/xxxx_add_v2_podcasts.py
git commit -m "migration: Add v2.0 content generation tables"
git push origin feature/v2-podcast-generation
```

### When Merging v2 → v1

The v2 migration files will merge into v1's alembic/versions/ directory naturally:

```bash
# When merging v2 branch into v1 main
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git merge feature/v2-podcast-generation

# The migration file comes along
# Database already has the tables (from v2 development)
# Alembic sees: "head revision already applied" ✅
```

---

## Rollback Strategy

### If v2 Migration Goes Wrong

```bash
# Downgrade to before v2 migration
alembic downgrade -1

# Or downgrade to specific revision
alembic downgrade abc123  # Last v1 revision

# Tables are dropped, v1 works normally
```

### Emergency: Drop All v2 Tables

```sql
-- Connect to database
psql -d hero_evidence_library

-- Drop v2 tables (preserves v1)
DROP TABLE IF EXISTS slide_decks CASCADE;
DROP TABLE IF EXISTS infographics CASCADE;
DROP TABLE IF EXISTS summaries CASCADE;
DROP TABLE IF EXISTS podcasts CASCADE;

-- Drop enum type
DROP TYPE IF EXISTS summarytype CASCADE;

-- Update alembic version back to v1
UPDATE alembic_version SET version_num = 'abc123';  -- Last v1 revision
```

---

## Testing Checklist

Before deploying v2 migration to production:

- [ ] Migration generated without errors
- [ ] Reviewed SQL in migration file
- [ ] Tested migration on local dev database
- [ ] Verified v1 app still works (no errors in logs)
- [ ] Verified v2 app can access new tables
- [ ] Tested rollback (downgrade migration)
- [ ] Committed migration file to git
- [ ] Documented any manual steps needed

---

## Production Deployment Plan

When v2 is ready for production (Mac Mini):

### Option A: Low-Risk Deployment
```bash
# On Mac Mini
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library

# Stop services
sudo systemctl stop bibliography-backend

# Pull v2 changes (includes migration)
git pull origin main  # After merging v2

# Run migration
cd backend
alembic upgrade head

# Restart services
sudo systemctl start bibliography-backend
```

### Option B: Zero-Downtime Deployment
1. New tables don't affect v1 (additive only)
2. Run migration while v1 is running ✅
3. Tables created in background
4. Deploy v2 code when ready
5. Features appear gradually

---

## Advantages of This Approach

### For Development
- ✅ Test v2 features with real production data
- ✅ No data synchronization scripts
- ✅ Shared user accounts
- ✅ Can reference existing papers in podcasts
- ✅ Simple connection configuration

### For Production
- ✅ Seamless merge when v2 ready
- ✅ No database migration during merge
- ✅ No downtime required
- ✅ Can deploy incrementally
- ✅ Easy rollback if needed

### For Users
- ✅ One account works everywhere
- ✅ Papers + podcasts in same interface
- ✅ No data migration/export needed
- ✅ Smooth feature rollout

---

## Alternative: Schema Separation (If Needed Later)

If you later want more isolation, PostgreSQL schemas provide a middle ground:

```sql
-- Create v2 schema
CREATE SCHEMA v2_dev;

-- v2 tables go in separate namespace
CREATE TABLE v2_dev.podcasts (...);

-- Can still reference v1 tables
ALTER TABLE v2_dev.podcasts 
  ADD FOREIGN KEY (user_id) REFERENCES public.users(id);
```

But this adds complexity without much benefit for your use case.

---

## Recommendation: Proceed with Shared Database

**Next Steps**:
1. Integrate v2 models into db.py
2. Generate Alembic migration
3. Test migration locally
4. Verify both v1 and v2 work
5. Commit migration file

This gives you the fastest path to working v2 features while keeping v1 completely safe.

---

**Created**: 2025-01-04  
**Status**: Ready to implement  
**Risk Level**: Low (additive only)
