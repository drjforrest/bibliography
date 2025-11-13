# Test Workflow: CSV Import from DEVONthink

## Quick Test with a Few Papers

### Step 1: Clear Existing Data

First, get your user ID:

```bash
cd /Users/drjforrest/dev/hero-counterforce/hero_evidence_library/backend

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

Clear the database (keeps files by default):

```bash
python scripts/clear_papers.py --user-id YOUR_USER_ID
```

Or clear everything including files:

```bash
python scripts/clear_papers.py --user-id YOUR_USER_ID --delete-files
```

### Step 2: Prepare Test Papers in DEVONthink

1. Select **3-5 papers** in DEVONthink for testing
2. These should be papers with:
   - Valid PDF files
   - Some metadata (name, comment, label, etc.)

### Step 3: Run Smart Rule in DEVONthink

Your AppleScript Smart Rule will export to:
- **CSV**: `/Users/drjforrest/PDFs/Evidence_Library_Sync/active_library.csv`
- **PDFs**: `/Users/drjforrest/PDFs/Evidence_Library_Sync/{uuid}.pdf`

Run the Smart Rule on your selected records.

### Step 4: Verify Export

Check that files were created:

```bash
# Check CSV exists and has content
ls -lh ~/PDFs/Evidence_Library_Sync/active_library.csv
cat ~/PDFs/Evidence_Library_Sync/active_library.csv

# Check PDFs were copied
ls -lh ~/PDFs/Evidence_Library_Sync/*.pdf

# Count PDFs
ls -1 ~/PDFs/Evidence_Library_Sync/*.pdf | wc -l
```

You should see:
- CSV file with header row + one row per paper
- PDF files named with UUIDs

### Step 5: Run Import Script

```bash
cd /Users/drjforrest/dev/hero-counterforce/hero_evidence_library

python backend/scripts/import_from_devonthink_csv.py \
  --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
  --user-id YOUR_USER_ID
```

You should see output like:

```
2025-01-13 10:23:45 - INFO - Starting import from /Users/drjforrest/PDFs/Evidence_Library_Sync/active_library.csv
2025-01-13 10:23:45 - INFO - Created search space: DEVONthink Import
2025-01-13 10:23:46 - INFO - Importing: Research Paper 1.pdf
2025-01-13 10:23:47 - INFO - Copying PDF to storage...
2025-01-13 10:23:47 - INFO - PDF stored at: 2025/01/abc-123-def.pdf
2025-01-13 10:23:48 - INFO - Extracting PDF content...
2025-01-13 10:23:49 - INFO - Created paper record: 1
2025-01-13 10:23:50 - INFO - Generating thumbnail...
2025-01-13 10:23:51 - INFO - Thumbnail generated: 2025/01/1.jpg
2025-01-13 10:23:52 - INFO - Vectorizing content...
2025-01-13 10:23:53 - INFO - Vectorization complete
2025-01-13 10:23:53 - INFO - Successfully imported: Research Paper 1.pdf
...

======================================================================
Import Summary
======================================================================
Successfully imported: 3
Skipped (already exists or no PDF): 0
Errors: 0

Next steps:
1. View imported papers at: http://localhost:3000/library
2. Thumbnails have been generated automatically
3. Papers are ready for semantic search
======================================================================
```

### Step 6: Verify Import

Check database:

```bash
python -c "
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine
from app.db import ScientificPaper
from app.config import config

async def count_papers():
    engine = create_async_engine(config.DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(select(func.count()).select_from(ScientificPaper))
        count = result.scalar()
        print(f'Papers in database: {count}')

        result = await conn.execute(select(ScientificPaper).limit(5))
        papers = result.fetchall()
        print('\nRecent papers:')
        for paper in papers:
            print(f'  - {paper.title} (ID: {paper.id})')
    await engine.dispose()

asyncio.run(count_papers())
"
```

Check files:

```bash
# Count PDFs in storage
find ~/dev/hero-counterforce/hero_evidence_library/data/pdfs -name "*.pdf" | wc -l

# Count thumbnails
find ~/dev/hero-counterforce/hero_evidence_library/data/thumbnails -name "*.jpg" | wc -l

# View storage structure
tree -L 3 ~/dev/hero-counterforce/hero_evidence_library/data/
```

### Step 7: Start Servers and View

```bash
# Terminal 1 - Backend
cd /Users/drjforrest/dev/hero-counterforce/hero_evidence_library/backend
python main.py --reload

# Terminal 2 - Frontend
cd /Users/drjforrest/dev/hero-counterforce/hero_evidence_library/frontend/nextjs-app
npm run dev
```

Visit: http://localhost:3000/library

### Step 8: Test in UI

**Library View:**
- ✅ Should see 3-5 book cards
- ✅ Each should have a thumbnail (not purple gradient)
- ✅ Hover should show chat button

**Click a Paper:**
- ✅ Should open paper detail page
- ✅ PDF should display in viewer
- ✅ Zoom controls should work
- ✅ Annotations sidebar on right

**Test Search:**
- ✅ Use search box to find papers
- ✅ Semantic search should work

**Test Chat:**
- ✅ Click chat button on a paper
- ✅ Chat panel should open
- ✅ Ask a question about the paper

## Troubleshooting Test

### CSV Not Created
```bash
# Check if directory exists
ls -la ~/PDFs/Evidence_Library_Sync/

# If not, Smart Rule might need path adjustment
# Or run manually:
mkdir -p ~/PDFs/Evidence_Library_Sync
```

### Import Shows Errors
Check logs for specific errors:
- "PDF file not found" → Smart Rule didn't copy PDF
- "Paper already imported" → Need to clear database first
- "Invalid user ID" → Check user ID format (UUID)

### Thumbnails Not Showing
```bash
# Check if Pillow is installed
pip list | grep -i pillow

# If not:
pip install Pillow

# Check thumbnail directory
ls -la ~/dev/hero-counterforce/hero_evidence_library/data/thumbnails/
```

### PDF Not Displaying
- Check browser console (F12) for errors
- Verify you're logged in
- Check if PDF endpoint works:
  ```bash
  curl http://localhost:8000/api/v1/papers/1/pdf \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -o test.pdf
  ```

## After Successful Test

Once you verify the 3-5 papers work correctly:

### Option 1: Import More Papers

1. Select more papers in DEVONthink
2. Run Smart Rule again
3. Re-run import script (will skip existing papers)

```bash
python backend/scripts/import_from_devonthink_csv.py \
  --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
  --user-id YOUR_USER_ID
```

### Option 2: Clear and Import Full Library

1. Clear database again:
   ```bash
   python scripts/clear_papers.py --user-id YOUR_USER_ID --delete-files
   ```

2. Select ALL papers in DEVONthink
3. Run Smart Rule (may take a while)
4. Import all:
   ```bash
   python backend/scripts/import_from_devonthink_csv.py \
     --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
     --user-id YOUR_USER_ID
   ```

### Option 3: Organize by Search Spaces

Create separate search spaces for different topics:

```python
# backend/scripts/create_search_spaces.py
import asyncio
from app.db import SearchSpace
from app.config import config
from sqlalchemy.ext.asyncio import create_async_engine
from uuid import UUID

async def create_spaces(user_id: UUID):
    engine = create_async_engine(config.DATABASE_URL)
    async with engine.begin() as conn:
        spaces = [
            {"name": "AI Research", "description": "Papers on AI and ML"},
            {"name": "Neuroscience", "description": "Neuroscience papers"},
            {"name": "Philosophy", "description": "Philosophy papers"},
        ]
        for space in spaces:
            # Create space...
            pass
```

Then import to specific spaces:

```bash
python backend/scripts/import_from_devonthink_csv.py \
  --csv ~/PDFs/Evidence_Library_Sync/ai_papers.csv \
  --user-id YOUR_USER_ID \
  --search-space-id 1
```

## Expected Timeline

For initial test with 3-5 papers:
- **Smart Rule**: 30-60 seconds
- **Import**: 1-2 minutes per paper
- **Total**: ~5-10 minutes

For full library (e.g., 500 papers):
- **Smart Rule**: 5-15 minutes
- **Import**: 3-4 hours
- **Total**: ~4 hours (can run overnight)

## Success Criteria

Your test is successful when:
- ✅ All papers imported (0 errors in summary)
- ✅ Thumbnails display in library view
- ✅ PDFs open and display correctly
- ✅ Search finds papers
- ✅ Chat responds to questions about papers
- ✅ No errors in browser console
- ✅ No errors in backend logs

## Next Steps After Testing

1. **Document your workflow** - Note any changes to Smart Rule
2. **Plan full import** - Schedule time for full library import
3. **Set up monitoring** - Regular exports from DEVONthink
4. **Backup strategy** - Backup database and PDF storage
5. **User training** - Document how to use the system

You're ready to test! 🚀
