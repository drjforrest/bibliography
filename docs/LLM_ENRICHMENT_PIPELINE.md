# LLM Enrichment Pipeline Implementation

## Overview

The HERO Evidence Library now features a comprehensive **LLM enrichment pipeline** that automatically enhances all papers with AI-generated content. This enrichment happens automatically for **both ingestion paths** (manual upload and DEVONthink sync), ensuring every paper receives rich metadata for improved discovery and understanding.

**Implementation Date**: December 21, 2025

## What Was Implemented

### ✅ LLM Enrichment Service

A reusable service that generates AI-powered enhancements for all scientific papers:

#### Generated Content
1. **Lay Summary** (2-3 paragraphs)
   - Accessible language for non-expert audiences
   - Explains research in plain English
   - Stored in `ScientificPaper.lay_summary` field

2. **Short Description** (1-2 sentences)
   - Concise overview for quick scanning
   - Stored in `extraction_metadata.short_description`

3. **Key Insights** (3-5 bullet points)
   - Main findings and implications
   - Stored as array in `extraction_metadata.insights`

4. **Multiple Citation Formats**
   - APA, MLA, Chicago, IEEE, Harvard, BibTeX
   - Stored in `extraction_metadata.citations`

#### Technical Details
- **Service**: `backend/app/services/llm_enrichment_service.py`
- **LLM Provider**: LM Studio (OpenAI-compatible API)
- **Endpoint**: `http://192.168.1.81:1234/v1`
- **Model**: `nvidia-nemotron-3-nano-30b-a3b-mlx`
- **Max Tokens**: 500 (lay summary), 200 (short description), 1200 (insights)

### ✅ Dual Ingestion Path Integration

Both paper ingestion paths now automatically trigger **complete enrichment pipelines**:

#### Path 1: Manual PDF Upload
**Flow**:
```
User uploads PDF via UI
    ↓
PDF processed & metadata extracted
    ↓
Paper record created in database
    ↓
Enrichment Pipeline Triggered:
    ├─ Step 1: Vectorization
    │   ├─ Document embedding generated
    │   └─ Text chunked and embedded
    └─ Step 2: LLM Enrichment
        ├─ Lay summary generated
        ├─ Short description generated
        ├─ Key insights extracted
        └─ Citations formatted
```

**Modified Service**: `backend/app/services/paper_manager.py`
- Added `EmbeddingService` and `LLMEnrichmentService` instances
- Created `_enrich_paper()` method for dual-pipeline processing
- Triggered automatically after paper creation (line 110)

#### Path 2: DEVONthink Sync
**Flow**:
```
DEVONthink sync initiated
    ↓
PDF copied from DEVONthink database
    ↓
Paper record created with DT metadata
    ↓
Enrichment Pipeline Triggered:
    ├─ Step 1: Vectorization
    │   ├─ Document embedding generated
    │   └─ Text chunked and embedded
    └─ Step 2: LLM Enrichment
        ├─ Lay summary generated
        ├─ Short description generated
        ├─ Key insights extracted
        └─ Citations formatted
```

**Modified Service**: `backend/app/services/devonthink_sync_service.py`
- Added `LLMEnrichmentService` instance
- Modified `_process_for_search()` to include LLM enrichment
- Runs after vectorization (lines 600-610)

## Backend Architecture

### Service Layer

```
backend/app/services/
├── llm_enrichment_service.py          # NEW - LLM enrichment service
├── embedding_service.py               # EXISTING - Vectorization service
├── paper_manager.py                   # UPDATED - Manual upload path
└── devonthink_sync_service.py         # UPDATED - DEVONthink sync path
```

### Database Schema

LLM-generated content is stored in the `ScientificPaper` model:

```python
class ScientificPaper:
    # Direct fields
    lay_summary: Optional[str]           # 2-3 paragraph accessible summary

    # JSON metadata fields (in extraction_metadata)
    extraction_metadata: dict = {
        "short_description": str,         # 1-2 sentence overview
        "insights": List[str],            # 3-5 key findings
        "citations": {                    # Multiple citation formats
            "apa": str,
            "mla": str,
            "chicago": str,
            "ieee": str,
            "harvard": str,
            "bibtex": str
        }
    }
```

## API Integration

### Backend API (FastAPI)

**Schema Updates**: `backend/app/schemas/papers.py`

```python
class PaperResponse(BaseModel):
    # ... other fields ...
    summary: Optional[str]                # DEVONthink Finder Comment
    lay_summary: Optional[str]            # LLM-generated accessible summary
    short_description: Optional[str]      # LLM-generated concise description
    insights: List[str]                   # LLM-generated key insights
    citations: Optional[Dict[str, str]]   # Multiple citation formats
```

The `from_orm()` method extracts LLM fields from `extraction_metadata`:

```python
@classmethod
def from_orm(cls, obj: ScientificPaper):
    # ... extract basic fields ...

    # Extract LLM enrichment from extraction_metadata
    if obj.extraction_metadata:
        metadata = obj.extraction_metadata
        data['short_description'] = metadata.get('short_description')
        data['insights'] = metadata.get('insights', [])
        data['citations'] = metadata.get('citations', {})

    return cls(**data)
```

## Frontend Integration

### Next.js TypeScript Types

**File**: `frontend/nextjs-app/types/index.ts`

```typescript
export interface Paper {
  // ... other fields ...
  summary?: string;              // DEVONthink Finder Comment
  lay_summary?: string;          // LLM-generated accessible summary
  short_description?: string;    // LLM-generated concise description
  insights?: string[];           // LLM-generated key insights
  citations?: Record<string, string>;  // Multiple citation formats
}
```

### UI Components

#### BookCard Component
**File**: `frontend/nextjs-app/components/library/BookCard.tsx`

Shows short description in hover tooltip:
```typescript
title={`${paper.title}\n\n${paper.short_description || paper.summary || 'No summary available'}`}
```

#### AnnotationSidebar Component
**File**: `frontend/nextjs-app/components/annotations/AnnotationSidebar.tsx`

Displays all LLM enrichment fields:

1. **Short Description** (most prominent)
   - Highlighted with teal accent border
   - Background color distinguishes it from other content

2. **Lay Summary** (expandable section)
   - Labeled "Lay Summary" for clarity
   - Accessible language explanation

3. **Key Insights** (expandable list)
   - Numbered list (1, 2, 3...)
   - Shows count in header
   - Lightbulb icon indicator

#### Paper Detail Page
**File**: `frontend/nextjs-app/app/papers/[paperId]/page.tsx`

Passes all LLM fields to sidebar:
```typescript
<AnnotationSidebar
  annotations={annotations}
  paperTitle={paper?.title || 'Document'}
  paperSummary={paper?.summary}
  shortDescription={paper?.short_description}
  laySummary={paper?.lay_summary}
  insights={paper?.insights}
/>
```

### Streamlit Integration

**File**: `frontend/app.py`

Also updated to display LLM fields in the Streamlit interface:

```python
# Short description (prominent)
if paper.get("short_description"):
    st.info(paper["short_description"])

# Lay summary (expandable)
if paper.get("lay_summary"):
    with st.expander("📖 Lay Summary"):
        st.write(paper["lay_summary"])

# Key insights (expandable)
if paper.get("insights"):
    with st.expander(f"💡 Key Insights ({len(paper['insights'])})"):
        for i, insight in enumerate(paper["insights"], 1):
            st.write(f"{i}. {insight}")
```

## Error Handling & Resilience

Both ingestion paths implement **graceful error handling**:

### Manual Upload Path
```python
# Don't fail the whole upload if enrichment fails
try:
    await self._enrich_paper(paper_id, search_space_id)
except Exception as e:
    logger.warning(f"Enrichment pipeline failed for paper {paper_id}: {str(e)}")
    # Continue - paper is still created and usable
```

### DEVONthink Sync Path
```python
# Continue sync even if vectorization/enrichment fails
try:
    # ... vectorization and LLM enrichment ...
except Exception as e:
    logger.error(f"Error processing paper {paper.id}: {str(e)}")
    # Documents are still stored and synced
```

**Key Benefits**:
- Papers are always created successfully
- Partial enrichment is acceptable
- Enrichment can be retried later
- Logs provide debugging information

## Running Manual Enrichment

For papers that need re-enrichment or were created before this feature:

### Batch Script
**File**: `backend/scripts/enrich_papers_llm.py`

```bash
cd backend

# Enrich all papers missing LLM content
python scripts/enrich_papers_llm.py --skip-existing

# Enrich specific number of papers
python scripts/enrich_papers_llm.py --limit 100

# Force re-enrichment of all papers
python scripts/enrich_papers_llm.py

# Custom batch size (default: 5)
python scripts/enrich_papers_llm.py --batch-size 10
```

**Features**:
- Progress tracking with statistics
- Error logging and recovery
- Configurable batch size
- Skip already-enriched papers
- Summary report at completion

## Configuration

### Environment Variables

```bash
# LLM API Configuration (in backend/.env)
FAST_LLM_API_BASE=http://192.168.1.81:1234/v1
FAST_LLM=nvidia-nemotron-3-nano-30b-a3b-mlx

# Alternative fallback
LLM_API_BASE=http://192.168.1.81:1234/v1
```

### LM Studio Setup

1. **Start LM Studio** on the server machine (192.168.1.81)
2. **Load Model**: `nvidia-nemotron-3-nano-30b-a3b-mlx`
3. **Enable API Server**: Settings → Enable API server on port 1234
4. **Verify**: `curl http://192.168.1.81:1234/v1/models`

## Performance Characteristics

### Timing Estimates (per paper)

| Operation | Approximate Time |
|-----------|-----------------|
| Vectorization | 5-15 seconds |
| Lay Summary | 10-20 seconds |
| Short Description | 5-10 seconds |
| Insights | 15-25 seconds |
| Citations | <1 second |
| **Total per paper** | **35-70 seconds** |

### Batch Processing

- **Recommended batch size**: 5 papers
- **Sequential processing**: Prevents API overload
- **Error tolerance**: Individual failures don't stop batch
- **Progress logging**: Every 10 papers

## Benefits & Use Cases

### For Researchers
- **Quick Understanding**: Short descriptions for rapid scanning
- **Accessible Explanations**: Lay summaries for cross-disciplinary work
- **Key Takeaways**: Insights highlight main findings
- **Easy Citations**: Multiple formats ready to use

### For Librarians
- **Enhanced Discovery**: Better metadata for search and filtering
- **Quality Assurance**: AI-generated summaries complement originals
- **User Support**: Multiple explanation levels for different audiences

### For Developers
- **API Richness**: More metadata available via REST API
- **Reusable Service**: Single service for all enrichment needs
- **Extensible**: Easy to add new LLM-generated fields

## Monitoring & Logs

### Log Messages to Watch

```bash
# Successful enrichment
INFO: Starting enrichment pipeline for paper 123
INFO: Step 1/2: Generating embeddings for paper 123
INFO: Successfully embedded document 456
INFO: Step 2/2: Running LLM enrichment for paper 123
INFO: Successfully enriched paper 123 with LLM-generated content
INFO: Completed enrichment pipeline for paper 123

# Partial failure (continues processing)
WARNING: Enrichment pipeline failed for paper 123: Connection timeout
ERROR: LLM enrichment failed for paper 123: API rate limit exceeded
```

### Debugging

Check enrichment status in database:
```sql
-- Papers missing LLM enrichment
SELECT id, title
FROM scientific_papers
WHERE lay_summary IS NULL
   OR extraction_metadata->>'short_description' IS NULL;

-- Papers with complete enrichment
SELECT id, title,
       CASE WHEN lay_summary IS NOT NULL THEN '✓' ELSE '✗' END as lay_summary,
       CASE WHEN extraction_metadata->>'short_description' IS NOT NULL THEN '✓' ELSE '✗' END as short_desc,
       CASE WHEN extraction_metadata->'insights' IS NOT NULL THEN '✓' ELSE '✗' END as insights
FROM scientific_papers;
```

## Future Enhancements

Potential improvements for the enrichment pipeline:

1. **Additional LLM Fields**
   - Research questions addressed
   - Methodology summary
   - Limitations and caveats
   - Related work recommendations

2. **Multi-Model Support**
   - Use specialized models for different tasks
   - Fallback to alternative models on failure
   - Model routing based on paper domain

3. **Incremental Updates**
   - Re-enrich on paper updates
   - Version tracking for LLM outputs
   - Comparison of enrichment over time

4. **User Feedback**
   - Rate LLM-generated content
   - Request re-generation
   - Manual corrections that inform future enrichment

## Related Documentation

- **DEVONthink Sync**: `DEVONTHINK_CSV_WORKFLOW.md`
- **Semantic Search**: `CLAUDE.md` (semantic_search_service section)
- **API Documentation**: Backend `/docs` endpoint (FastAPI auto-generated)
- **Frontend Components**: `frontend/nextjs-app/components/annotations/`

## Troubleshooting

### LLM Enrichment Not Running

1. **Check LM Studio**:
   ```bash
   curl http://192.168.1.81:1234/v1/models
   ```

2. **Check Environment Variables**:
   ```bash
   cd backend
   grep LLM .env
   ```

3. **Check Logs**:
   ```bash
   tail -f logs/app.log | grep -i enrich
   ```

### Papers Missing Enrichment

Run the batch enrichment script:
```bash
cd backend
python scripts/enrich_papers_llm.py --skip-existing
```

### Slow Processing

Adjust batch size and timeouts:
```python
# In llm_enrichment_service.py
self.timeout = aiohttp.ClientTimeout(total=600)  # Increase to 10 min

# In enrich_papers_llm.py
pipeline = LLMEnrichmentPipeline(session_maker, batch_size=3)  # Smaller batches
```

## Support

For issues or questions:
- Check logs: `backend/logs/app.log`
- Review this documentation
- Examine code: `backend/app/services/llm_enrichment_service.py`
