# Bidirectional Sync Guide: Library ↔ DEVONthink

## Overview

The bibliography system supports **one-way sync from DEVONthink → Library** (currently implemented). This guide explains how to identify papers that need to be synced **back to DEVONthink** (Library → DEVONthink) to complete bidirectional syncing.

## How It Works

### Identifying Papers for Export

Papers are marked with their source:
- **From DEVONthink**: Have `dt_source_uuid` set (DEVONthink UUID)
- **Uploaded by users**: Have `dt_source_uuid = NULL`

### Uploaded Papers Get Full Enrichment

When users upload PDFs via `/api/v1/papers/upload`, they go through the **same enrichment pipeline** as DEVONthink-synced papers:

1. ✅ **PDF Processing**: Metadata extraction (title, authors, DOI, abstract)
2. ✅ **File Storage**: UUID-based storage with deduplication
3. ✅ **Vectorization**: Embeddings and chunks for semantic search
4. ✅ **LLM Enrichment**: Lay summary, short description, insights, citations
5. ✅ **Thumbnail Generation**: First-page thumbnails for library view

This means uploaded papers are fully processed and searchable, just like DEVONthink papers!

## Finding Papers to Export

### Method 1: API Endpoint (Recommended)

Use the API to get papers that need DEVONthink export:

```bash
GET /api/v1/papers/for-devonthink-export?limit=100
```

Returns papers with `dt_source_uuid = NULL` (uploaded papers, not from DEVONthink).

### Method 2: Script

Run the Python script to list or export papers:

```bash
# List papers that need export
cd backend
python scripts/list_papers_for_devonthink_export.py

# Filter by user
python scripts/list_papers_for_devonthink_export.py --user-id YOUR_USER_ID

# Export to CSV for review
python scripts/list_papers_for_devonthink_export.py --export-csv papers_to_export.csv
```

## Exporting Papers to DEVONthink

Once you've identified papers to export, you have two options:

### Option 1: Manual Export (Recommended for now)

1. **Get list of papers** (via API or script)
2. **Download PDFs** from the library
3. **Import to DEVONthink** manually or via DEVONthink's import features
4. **Update database** to link the paper to DEVONthink:

```sql
-- After importing to DEVONthink, update dt_source_uuid
UPDATE scientific_papers 
SET dt_source_uuid = 'DEVONTHINK-UUID-HERE',
    dt_source_path = '/DEVONthink/Path/Here'
WHERE id = PAPER_ID;
```

### Option 2: Automated Export (Future Enhancement)

An automated export service could:
- Query papers with `dt_source_uuid = NULL`
- Copy PDFs to a staging directory
- Use DEVONthink MCP server to create records
- Update `dt_source_uuid` after successful import
- Handle duplicates and errors

**This is not yet implemented** but could be added if needed.

## Workflow Example

### Current State: One-Way Sync

```
DEVONthink → [Sync Process] → Library ✅
Library → DEVONthink ❌ (Manual)
```

### Future State: Bidirectional Sync

```
DEVONthink ↔ [Bidirectional Sync] ↔ Library ✅
```

## Database Schema

### ScientificPaper Table

```python
dt_source_uuid: String(255)  # NULL = uploaded by user, not from DEVONthink
dt_source_path: Text          # DEVONthink path (if from DEVONthink)
```

### DevonthinkSync Table

Tracks DEVONthink → Library syncs only. For bidirectional sync, you'd need to track:
- Library → DEVONthink exports (not yet implemented)

## Next Steps

1. ✅ **Identify papers**: Use API endpoint or script
2. ✅ **Review papers**: Check which ones you want in DEVONthink
3. ⏳ **Export to DEVONthink**: Manual import for now
4. ⏳ **Link records**: Update `dt_source_uuid` after import
5. ⏳ **Future**: Automated export service

## Example: Using the API

```python
import requests

# Get your auth token (Clerk)
token = "your-clerk-token"

# Get papers that need export
response = requests.get(
    "https://your-api.com/api/v1/papers/for-devonthink-export",
    headers={"Authorization": f"Bearer {token}"},
    params={"limit": 100}
)

papers = response.json()["papers"]
print(f"Found {len(papers)} papers to export to DEVONthink")

for paper in papers:
    print(f"- {paper['title']} (ID: {paper['id']})")
    # Download PDF
    # Import to DEVONthink
    # Update dt_source_uuid
```

## Summary

- ✅ **Uploaded papers get full enrichment** (same as DEVONthink papers)
- ✅ **API endpoint available** to find papers for export
- ✅ **Script available** to list/export papers
- ⏳ **Automated export** not yet implemented (manual for now)
- ⏳ **After importing to DEVONthink**, update `dt_source_uuid` to complete the link

