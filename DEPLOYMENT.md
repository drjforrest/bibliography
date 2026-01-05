# v1 Deployment Update Guide

## What Changed

### Database Schema Updates (MANUAL - Run in TablePlus)

#### 1. Create Missing v2 Tables
```sql
-- Drop and recreate infographics table
DROP TABLE IF EXISTS infographics CASCADE;
CREATE TABLE infographics (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    title VARCHAR(500) NOT NULL,
    infographic_type VARCHAR(50) NOT NULL,
    file_location TEXT,
    file_format VARCHAR(10),
    file_size_bytes INTEGER,
    data_json JSON,
    source_paper_ids INTEGER[] NOT NULL DEFAULT '{}',
    user_prompt TEXT,
    generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    generation_error TEXT,
    task_id VARCHAR(255),
    search_space_id INTEGER REFERENCES searchspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
);

CREATE INDEX idx_infographics_task_id ON infographics(task_id);
CREATE INDEX idx_infographics_created_at ON infographics(created_at);

-- Create slide_decks table
DROP TABLE IF EXISTS slide_decks CASCADE;
CREATE TABLE slide_decks (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    title VARCHAR(500) NOT NULL,
    slide_count INTEGER,
    file_location TEXT,
    file_format VARCHAR(10),
    file_size_bytes INTEGER,
    slides_json JSON,
    source_paper_ids INTEGER[] NOT NULL DEFAULT '{}',
    user_prompt TEXT,
    generation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    generation_error TEXT,
    task_id VARCHAR(255),
    search_space_id INTEGER REFERENCES searchspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
);

CREATE INDEX idx_slide_decks_task_id ON slide_decks(task_id);
CREATE INDEX idx_slide_decks_created_at ON slide_decks(created_at);
```

#### 2. Add API Key Storage to User Table
```sql
ALTER TABLE "user" 
ADD COLUMN IF NOT EXISTS openai_api_key VARCHAR(255),
ADD COLUMN IF NOT EXISTS elevenlabs_api_key VARCHAR(255);
```

### Frontend Changes (AUTOMATIC - via git pull)

**New Features:**
- ✅ Literature type filter component
- ✅ Filter integration in Topics page
- ✅ Automatic refetch on filter change
- ✅ Filter persistence during search

**Files Changed:**
- `frontend/nextjs-app/components/library/LiteratureFilter.tsx` (NEW)
- `frontend/nextjs-app/app/topics/page.tsx` (MODIFIED)

## Deployment Steps

### For Development (Mac Mini)

```bash
# 1. Pull latest code
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git pull origin main

# 2. Install any new dependencies (if needed)
cd frontend/nextjs-app
npm install

# 3. Restart the frontend dev server
# Kill the current process (Ctrl+C) and restart:
npm run dev

# 4. Execute the SQL scripts above in TablePlus
# (Connect to 192.168.1.69:5432/hero_evidence_library_prod)
```

### For Production Deployment

```bash
# 1. SSH into production server
ssh user@production-server

# 2. Navigate to project directory
cd /path/to/hero_evidence_library

# 3. Pull latest changes
git pull origin main

# 4. Rebuild frontend
cd frontend/nextjs-app
npm install
npm run build

# 5. Restart services
pm2 restart hero-evidence-library-frontend
# or however you manage your processes

# 6. Execute SQL migrations in production database
# Use your production database connection
```

## Verification Checklist

### After Update:

- [ ] Frontend starts without errors
- [ ] Topics page loads correctly
- [ ] Literature filter is visible with 4 options:
  - All Literature
  - Peer-Reviewed
  - Grey Literature  
  - News
- [ ] Clicking filter options updates the paper list
- [ ] Search still works with filter active
- [ ] Check TablePlus for new tables:
  - `infographics` (with task_id column)
  - `slide_decks` (with task_id column)
- [ ] Check `user` table for new columns:
  - `openai_api_key`
  - `elevenlabs_api_key`

## Rollback (If Needed)

If something breaks:

```bash
# Revert to previous commit
git reset --hard HEAD~1
git push -f origin main  # ONLY if deployment hasn't happened elsewhere

# Or revert specific commit
git revert e665687  # Literature filter commit
git push origin main
```

## Environment Variables

No new environment variables required for this update.

## Database Considerations

**IMPORTANT:** The SQL scripts use `IF NOT EXISTS` and `DROP TABLE IF EXISTS CASCADE` so they're safe to run multiple times. However:

- `DROP TABLE CASCADE` will delete any existing data in `infographics` and `slide_decks`
- If these tables already have data you want to keep, modify the scripts to use `ALTER TABLE` instead
- The `user` table alterations use `ADD COLUMN IF NOT EXISTS` so they're completely safe

## Known Issues

None currently. All changes are backwards compatible.

## Support

If issues arise:
1. Check browser console for frontend errors
2. Check backend logs for API errors  
3. Verify database connections in TablePlus
4. Review the troubleshooting section in `scripts/README.md`

---

**Deployed by:** Jamie Forrest  
**Date:** 2026-01-05  
**Commit:** e665687 - "feat: Add literature type filtering to frontend"