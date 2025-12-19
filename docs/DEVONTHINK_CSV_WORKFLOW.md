# DEVONthink CSV Import Workflow

## Overview

This workflow uses a DEVONthink Smart Rule to export PDFs and metadata to a CSV file, which is then imported into the Bibliography system. This approach is simpler than the MCP integration and gives you more control over what gets synced.

## Workflow Steps

### 1. Set Up DEVONthink Smart Rule

Your Smart Rule script exports to:
- **CSV File**: `~/PDFs/Evidence_Library_Sync/active_library.csv`
- **PDF Files**: `~/PDFs/Evidence_Library_Sync/{uuid}.pdf`

The CSV contains:
- DEVONthink UUID
- Name
- Single Sentence Description (from comment)
- RecordLabel
- Finder Comment
- PDF Path

### 2. Run the Smart Rule in DEVONthink

1. Select the records you want to export
2. Apply the Smart Rule (or set it to run automatically)
3. This will create/update the CSV and copy PDFs to the sync folder

### 3. Import into Bibliography System

Get your user ID first (you'll need this once):

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

Then run the import:

```bash
python backend/scripts/import_from_devonthink_csv.py \
  --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
  --user-id YOUR_USER_ID_HERE
```

### 4. View Your Library

Start the servers:

```bash
# Terminal 1 - Backend
cd backend
python main.py --reload

# Terminal 2 - Frontend
cd frontend/nextjs-app
npm run dev
```

Visit: http://localhost:3000/library

## What Happens During Import

For each record in the CSV:

1. **PDF Storage**: Copies PDF from sync folder to `data/pdfs/YYYY/MM/{uuid}.pdf`
2. **Metadata Extraction**: Extracts title, authors, DOI, etc. from PDF
3. **Database Records**: Creates `ScientificPaper` and `Document` records
4. **Thumbnail Generation**: Creates thumbnail from first page of PDF
5. **Vectorization**: Generates embeddings for semantic search

## Import Script Features

### Automatic Handling

- **Duplicate Detection**: Skips papers already imported (by DEVONthink UUID)
- **Missing PDFs**: Skips records where PDF file is missing
- **Metadata Fallback**: Uses DEVONthink description if abstract not found in PDF
- **Error Handling**: Continues import even if individual papers fail
- **Batch Vectorization**: Rebuilds vector store once at the end

### Output

The script provides:
- Real-time progress logging
- Summary statistics (imported, skipped, errors)
- Error details for troubleshooting

Example output:
```
2025-01-13 10:23:45 - INFO - Starting import from ~/PDFs/Evidence_Library_Sync/active_library.csv
2025-01-13 10:23:45 - INFO - Importing: Research on AI Safety.pdf
2025-01-13 10:23:46 - INFO - PDF stored at: 2025/01/abc-123-def.pdf
2025-01-13 10:23:47 - INFO - Created paper record: 42
2025-01-13 10:23:48 - INFO - Thumbnail generated: 2025/01/42.jpg
2025-01-13 10:23:49 - INFO - Vectorization complete
2025-01-13 10:23:49 - INFO - Successfully imported: Research on AI Safety.pdf
...

======================================================================
Import Summary
======================================================================
Successfully imported: 45
Skipped (already exists or no PDF): 5
Errors: 0

Next steps:
1. View imported papers at: http://localhost:3000/library
2. Thumbnails have been generated automatically
3. Papers are ready for semantic search
======================================================================
```

## Incremental Updates

To add new papers later:

1. **In DEVONthink**: Select new records and run the Smart Rule
   - The CSV is appended to (not overwritten)
   - New PDFs are added to the sync folder

2. **Run import again**: The script will skip already-imported papers
   ```bash
   python backend/scripts/import_from_devonthink_csv.py \
     --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
     --user-id YOUR_USER_ID
   ```

## Search Spaces

By default, imported papers go to a search space called "DEVONthink Import".

To specify a different search space:

```bash
# First, get search space ID
python -c "
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from app.db import SearchSpace
from app.config import config

async def list_spaces():
    engine = create_async_engine(config.DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(select(SearchSpace))
        spaces = result.fetchall()
        for space in spaces:
            print(f'Name: {space.name}, ID: {space.id}')
    await engine.dispose()

asyncio.run(list_spaces())
"

# Then use the ID in import
python backend/scripts/import_from_devonthink_csv.py \
  --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
  --user-id YOUR_USER_ID \
  --search-space-id 1
```

## Organizing Papers by Label

The DEVONthink `RecordLabel` is imported as a tag on the paper. You can:

- Filter papers by label/tag in the UI
- Create custom views based on labels
- Use labels for literature type categorization

## Metadata Mapping

| DEVONthink Field | Bibliography Field | Notes |
|------------------|-------------------|-------|
| Name | `title` | Fallback if PDF has no embedded title |
| Single Sentence Description | `abstract` | Fallback if PDF has no abstract |
| RecordLabel | `tags` | Array of tags |
| Finder Comment | `extraction_metadata.finder_comment` | Stored as metadata |
| DEVONthink UUID | `dt_source_uuid` | Used for duplicate detection |

## Troubleshooting

### Import fails with "User not found"

Make sure you're using the correct user ID (UUID format):
```bash
python backend/scripts/import_from_devonthink_csv.py \
  --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
  --user-id 12345678-1234-1234-1234-123456789abc
```

### Some papers are skipped

Check the logs for reasons:
- "Paper already imported" - Already in database
- "PDF file not found" - PDF wasn't copied by Smart Rule
- Check CSV for empty PDF Path values

### Thumbnails not generating

- Verify Pillow is installed: `pip install Pillow`
- Check that PDFs are valid (not corrupted)
- Look for errors in the import log

### CSV encoding issues

If you see encoding errors, try:
- Save CSV as UTF-8 in DEVONthink
- Check for special characters in record names

## Advanced: Custom Search Spaces by Label

You can create a script to import papers into different search spaces based on their label:

```python
# Create search spaces for each label
labels = ["Research", "Reference", "Teaching"]
for label in labels:
    # Create search space
    space = SearchSpace(name=label, user_id=user_id)
    session.add(space)

# Then filter CSV and import by label
for label in labels:
    filtered_records = [r for r in csv_records if r['RecordLabel'] == label]
    # Import into specific search space
```

## Comparison: CSV vs MCP Integration

| Feature | CSV Export | MCP Integration |
|---------|-----------|-----------------|
| **Setup** | Simple Smart Rule | Requires MCP server setup |
| **Control** | Full control over what's exported | Syncs entire database |
| **Folder Structure** | Flattened | Preserves hierarchy |
| **Incremental** | Manual re-run | Automatic monitoring |
| **Metadata** | Custom fields via CSV | Standard DEVONthink properties |
| **Best For** | Curated subsets | Full database sync |

## Recommended Workflow

1. **Initial Import**: Run Smart Rule on your entire library, import all papers
2. **Weekly Updates**: Select new papers, run Smart Rule, re-run import
3. **Periodic Cleanup**: Review skipped papers, regenerate thumbnails if needed
4. **Search Space Organization**: Create multiple search spaces for different topics

## Integration with UI

After import, papers are fully integrated:

- ✅ **Library View**: Book cards with thumbnails
- ✅ **PDF Viewer**: Click to view full PDF
- ✅ **Search**: Semantic search across all imported papers
- ✅ **Annotations**: Add notes and highlights
- ✅ **AI Chat**: Chat with individual papers or entire library
- ✅ **Citations**: Generate citations in multiple formats

## Next Steps

1. **Install Pillow**: `pip install Pillow`
2. **Get User ID**: Run the user ID query above
3. **Run Smart Rule**: Export your first batch from DEVONthink
4. **Import Papers**: Run the import script
5. **View Library**: Start servers and visit http://localhost:3000/library

Your papers will now be available with:
- Thumbnails automatically generated
- Full-text search enabled
- Semantic search powered by embeddings
- PDF viewing in the browser
