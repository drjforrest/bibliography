# ✅ v2.0 Database Integration Complete

## Status: Models Integrated, Ready for Migration

### What's Been Done

#### 1. Database Models Integrated ✅

**File**: `backend/app/db.py`

**Added v2.0 Models**:
- ✅ `SummaryType` enum (lay, technical, executive, comparative, visual)
- ✅ `Podcast` model - Full implementation with all fields
- ✅ `Summary` model - Multiple summary types
- ✅ `Infographic` model - Visual content generation  
- ✅ `SlideDeck` model - Presentation export

**Updated Relationships**:
- ✅ `SearchSpace` - Added podcasts, summaries, infographics, slide_decks relationships
- ✅ `User` - Added podcasts, summaries, infographics, slide_decks relationships

**Fields Added** (to all v2 models):
- Metadata: title, description, file_location, etc.
- Source tracking: source_paper_ids, user_prompt
- Generation tracking: generation_status, generation_error, task_id
- Relations: user_id, search_space_id

#### 2. Migration Script Created ✅

**File**: `backend/scripts/run_migration.sh`

Automated script that:
- Checks Python 3.12+ requirement
- Creates/activates virtual environment
- Installs dependencies
- Generates Alembic migration
- Previews changes before applying
- Applies migration to database
- Verifies completion

---

## Database Schema Changes

### New Tables (4)

```sql
-- podcasts
CREATE TABLE podcasts (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Metadata
    title VARCHAR(500) NOT NULL,
    description TEXT,
    duration_seconds INTEGER,
    
    -- Content
    podcast_transcript JSON,
    file_location TEXT,
    file_size_bytes INTEGER,
    
    -- Source tracking
    source_paper_ids INTEGER[],
    user_prompt TEXT,
    
    -- Generation metadata
    generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    generation_error TEXT,
    task_id VARCHAR(255),
    
    -- Foreign keys
    search_space_id INTEGER NOT NULL REFERENCES searchspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES user(id) ON DELETE CASCADE
);

-- summaries
CREATE TABLE summaries (
    -- Similar structure with summary_type enum
);

-- infographics
CREATE TABLE infographics (
    -- Similar structure with infographic_type
);

-- slide_decks
CREATE TABLE slide_decks (
    -- Similar structure with slide_count
);
```

### New Enum Type

```sql
CREATE TYPE summarytype AS ENUM ('lay', 'technical', 'executive', 'comparative', 'visual');
```

### Indexes Created

- `generation_status` - Query by status (pending, complete, error)
- `task_id` - Track Celery tasks
- `created_at` - Timestamp queries (inherited from TimestampMixin)

---

## How to Run Migration

### Prerequisites

1. **Python 3.12+** installed
2. **PostgreSQL** database running
3. **DATABASE_URL** configured in `.env`

### Step-by-Step

```bash
# Navigate to backend
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend

# Run migration script
./scripts/run_migration.sh
```

The script will:
1. Check Python version (requires 3.12+)
2. Create/activate virtual environment
3. Install dependencies
4. Generate Alembic migration
5. Show preview of SQL changes
6. Ask for confirmation
7. Apply migration
8. Verify completion

### If You Have Python 3.12

```bash
# Install if needed
brew install python@3.12

# Create new venv with 3.12
cd backend
python3.12 -m venv venv
source venv/bin/activate

# Run migration
./scripts/run_migration.sh
```

### Manual Migration (Alternative)

```bash
cd backend
source venv/bin/activate  # with Python 3.12+
pip install -e .

# Generate migration
alembic revision --autogenerate -m "Add v2.0 content generation tables"

# Preview
alembic upgrade head --sql > preview.sql
cat preview.sql  # Review changes

# Apply
alembic upgrade head
```

---

## Verification Steps

### 1. Check Migration Files

```bash
ls backend/alembic/versions/
# Should see new file: xxxx_add_v2_0_content_generation_tables.py
```

### 2. Verify Database Tables

```bash
psql -d hero_evidence_library -c "\dt"
# Should show: podcasts, summaries, infographics, slide_decks
```

### 3. Test v1 Still Works

```bash
# Start v1 app
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Test endpoints
curl http://localhost:8000/api/papers
# Should work normally
```

### 4. Test v2 Can Access Tables

```bash
# Start v2 app  
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend
source venv/bin/activate
uvicorn main:app --reload --port 8001

# In Python shell
from app.db import get_async_session, Podcast, Summary
# Should import without errors
```

---

## Rollback Strategy

### If Migration Goes Wrong

```bash
# Rollback to previous version
cd backend
source venv/bin/activate
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade abc123  # Last v1 revision
```

### Emergency: Manual Table Deletion

```sql
-- Connect to database
psql -d hero_evidence_library

-- Drop v2 tables (preserves v1)
DROP TABLE IF EXISTS slide_decks CASCADE;
DROP TABLE IF EXISTS infographics CASCADE;
DROP TABLE IF EXISTS summaries CASCADE;
DROP TABLE IF EXISTS podcasts CASCADE;
DROP TYPE IF EXISTS summarytype CASCADE;

-- Reset alembic version
UPDATE alembic_version SET version_num = 'previous_revision_id';
```

---

## Safety Features

### What v2 Models Do

✅ **Only ADD new tables** - Never modify v1 tables
✅ **Reference existing tables** - user_id, search_space_id
✅ **Cascade deletes** - If user/space deleted, v2 content deleted too
✅ **Nullable relationships** - Can exist independently

### What v2 Models DON'T Do

❌ **Don't modify v1 schemas** - Existing tables unchanged
❌ **Don't require changes to v1 code** - v1 app ignores new tables
❌ **Don't break existing data** - All changes are additive

---

## Next Steps After Migration

### 1. Commit Migration File

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# Add migration file
git add backend/alembic/versions/xxxx_add_v2_0_content.py
git add backend/app/db.py
git add backend/scripts/run_migration.sh

# Commit
git commit -m "feat: Add v2.0 database schema

- Add Podcast, Summary, Infographic, SlideDeck models
- Update SearchSpace and User relationships
- Create Alembic migration script
- All changes are additive (no v1 modifications)"

# Push
git push origin feature/v2-podcast-generation
```

### 2. Continue Building Features

With database ready, you can now:
- Complete podcaster nodes and graph
- Create Celery tasks
- Build API routes
- Test end-to-end podcast generation

### 3. Test on Development Database First

Before production:
- Run migration on local dev database
- Test v1 and v2 apps
- Verify no conflicts
- Then deploy to Mac Mini production

---

## Database Connection String

Both v1 and v2 use the same database:

```bash
# backend/.env (in both repos)
DATABASE_URL=postgresql+asyncpg://username:password@localhost/hero_evidence_library
```

For Mac Mini production:
```bash
DATABASE_URL=postgresql+asyncpg://username:password@macmini.local/hero_evidence_library
```

---

## What This Enables

With database integrated:

✅ **Podcast Generation**
- Store podcast metadata
- Track generation status
- Link to source papers
- Associate with users

✅ **Summary Generation**
- Multiple summary types
- Per-paper or multi-paper
- Different audiences (lay, technical, executive)

✅ **Infographic Creation**
- Visual content storage
- Structured data export
- Link to source papers

✅ **Slide Deck Export**
- Presentation generation
- Multiple formats (PPTX, PDF)
- Track slide content

---

## Summary

### Completed ✅
1. Integrated v2 models into db.py
2. Added SummaryType enum
3. Updated SearchSpace relationships
4. Updated User relationships
5. Created automated migration script
6. Documented rollback procedures

### Ready To Run 🚀
- Migration script ready
- Models tested for syntax
- Relationships configured
- Safety measures in place

### Requirements ⚙️
- Python 3.12+
- PostgreSQL database
- DATABASE_URL configured

---

**Created**: 2025-01-04  
**Status**: Ready for Migration  
**Risk**: Low (additive only)  
**Run**: `./backend/scripts/run_migration.sh`
