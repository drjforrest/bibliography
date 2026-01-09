# Running Enrichment on Production Server

This guide explains how to run the enrichment modules on the production server (mac-mini).

## Prerequisites

1. **SSH into the server**:
   ```bash
   ssh jforrest@mac-mini
   ```

2. **Navigate to backend directory**:
   ```bash
   cd ~/production/hero-evidence-library/backend
   ```

3. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

## Available Enrichment Scripts

There are **four** enrichment scripts available:

### ⭐ **NEW: Unified Enrichment** (`enrich_papers_unified.py`) - **RECOMMENDED**
**Coordinates ALL enrichment steps in the correct order:**
- DOI metadata enrichment (Crossref/Semantic Scholar)
- PDF processing (text extraction, metadata from PDF)
- Vectorization (embeddings and chunks)
- LLM enrichment (lay summaries, insights, citations)

**This is the recommended script** as it ensures papers get 100% enrichment.

### Legacy Scripts (Each does ~33% of the job):

There are three separate enrichment scripts available:

### 1. LLM Enrichment (`enrich_papers_llm.py`)
Generates AI-powered content:
- Lay summaries (accessible language)
- Short descriptions (1-2 sentences)
- Key insights (3-5 bullet points)
- Citations (multiple formats: APA, MLA, Chicago, etc.)

### 2. Full Pipeline (`enrich_papers_full_pipeline.py`)
Complete enrichment including:
- PDF text extraction
- Metadata extraction
- Vectorization (embeddings)
- LLM enrichment (lay summaries, insights, etc.)

### 3. DOI Metadata Backfill (`backfill_metadata_from_doi.py`)
Enriches papers with metadata from Crossref/Semantic Scholar APIs using DOI.

## Running Enrichment Scripts

### ⭐ Option 1: Unified Enrichment (RECOMMENDED)

**On-demand enrichment for a specific paper**:
```bash
# Enrich paper ID 1234
python scripts/enrich_papers_unified.py --paper-id 1234

# Enrich paper ID 1234, skip DOI enrichment
python scripts/enrich_papers_unified.py --paper-id 1234 --skip-doi
```

**Complete enrichment for all papers**:
```bash
python scripts/enrich_papers_unified.py
```

**Skip papers that already have enrichment**:
```bash
python scripts/enrich_papers_unified.py --skip-existing
```

**Limit to first N papers**:
```bash
python scripts/enrich_papers_unified.py --limit 100
```

**Skip specific steps** (if you only want certain enrichment):
```bash
# Only LLM + vectorization (skip DOI and PDF processing)
python scripts/enrich_papers_unified.py --skip-doi --skip-pdf

# Only DOI enrichment (skip everything else)
python scripts/enrich_papers_unified.py --skip-pdf --skip-vectorization --skip-llm
```

**Full example**:
```bash
python scripts/enrich_papers_unified.py --limit 100 --skip-existing --batch-size 5
```

### Option 2: LLM Enrichment Only (Legacy)

**Basic usage** (enrich all papers that need it):
```bash
python scripts/enrich_papers_llm.py
```

**Skip papers that already have lay summaries**:
```bash
python scripts/enrich_papers_llm.py --skip-existing
```

**Limit to first N papers** (useful for testing):
```bash
python scripts/enrich_papers_llm.py --limit 10
```

**Custom batch size** (default is 5):
```bash
python scripts/enrich_papers_llm.py --batch-size 10
```

**Full example with all options**:
```bash
python scripts/enrich_papers_llm.py --limit 100 --skip-existing --batch-size 5
```

### Option 3: Full Pipeline (Vectorization + LLM) (Legacy)

**Basic usage**:
```bash
python scripts/enrich_papers_full_pipeline.py
```

**Skip papers that already have full_text**:
```bash
python scripts/enrich_papers_full_pipeline.py --skip-existing
```

**Limit to first N papers**:
```bash
python scripts/enrich_papers_full_pipeline.py --limit 50
```

**Custom batch size** (default is 10):
```bash
python scripts/enrich_papers_full_pipeline.py --batch-size 5
```

### Option 4: DOI Metadata Backfill (Legacy)

**Basic usage**:
```bash
python scripts/backfill_metadata_from_doi.py
```

**Skip already enriched papers**:
```bash
python scripts/backfill_metadata_from_doi.py --skip-enriched
```

**Limit to first N papers**:
```bash
python scripts/backfill_metadata_from_doi.py --limit 50
```

## Running in Background

For long-running enrichment jobs, run in the background:

### Using `nohup` (Simple)

```bash
# LLM enrichment in background
nohup python scripts/enrich_papers_llm.py --skip-existing > ../logs/enrichment_llm.log 2>&1 &

# Full pipeline in background
nohup python scripts/enrich_papers_full_pipeline.py --skip-existing > ../logs/enrichment_full.log 2>&1 &
```

**Check progress**:
```bash
tail -f ../logs/enrichment_llm.log
```

**Check if still running**:
```bash
ps aux | grep enrich_papers
```

**Stop the process**:
```bash
# Find the process ID
ps aux | grep enrich_papers

# Kill it
kill <PID>
```

### Using `screen` (Recommended for long jobs)

```bash
# Start a new screen session
screen -S enrichment

# Run the enrichment script
python scripts/enrich_papers_llm.py --skip-existing

# Detach: Press Ctrl+A, then D
# Reattach: screen -r enrichment
# List sessions: screen -ls
```

### Using `tmux` (Alternative)

```bash
# Start a new tmux session
tmux new -s enrichment

# Run the enrichment script
python scripts/enrich_papers_llm.py --skip-existing

# Detach: Press Ctrl+B, then D
# Reattach: tmux attach -t enrichment
# List sessions: tmux ls
```

## Environment Variables

Make sure these are set in `backend/.env`:

```bash
# LLM API configuration
FAST_LLM_API_BASE=http://192.168.1.81:1234/v1  # or your LLM endpoint
FAST_LLM=nvidia-nemotron-3-nano-30b-a3b-mlx     # or your model name

# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost/bibliography_db

# Embedding model
EMBEDDING_MODEL=openai://nomic-embed-text
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=ollama
```

## Monitoring Progress

### Check Logs

```bash
# View recent logs
tail -n 100 ../logs/enrichment_llm.log

# Follow logs in real-time
tail -f ../logs/enrichment_llm.log

# Search for errors
grep -i error ../logs/enrichment_llm.log
```

### Check Database

```bash
# Connect to PostgreSQL
psql -d bibliography_db

# Count papers with lay summaries
SELECT COUNT(*) FROM scientific_papers WHERE lay_summary IS NOT NULL AND lay_summary != '';

# Count papers with insights
SELECT COUNT(*) FROM scientific_papers WHERE extraction_metadata->>'insights' IS NOT NULL;
```

## Recommended Workflow

### ⭐ **Recommended: Use Unified Enrichment**

For complete enrichment of all papers, use the unified script:

```bash
# Complete enrichment (all steps) for all papers
nohup python scripts/enrich_papers_unified.py --skip-existing > ../logs/enrichment_unified.log 2>&1 &

# Monitor progress
tail -f ../logs/enrichment_unified.log
```

This single command will:
1. ✅ Fetch DOI metadata from Crossref/Semantic Scholar
2. ✅ Extract full_text and metadata from PDFs
3. ✅ Generate embeddings and chunks for semantic search
4. ✅ Generate LLM content (lay summaries, insights, citations)

### Legacy Workflow (if you need separate steps)

If you need to run enrichment steps separately:

1. **First, run full pipeline** (if papers need vectorization):
   ```bash
   nohup python scripts/enrich_papers_full_pipeline.py --skip-existing > ../logs/enrichment_full.log 2>&1 &
   ```

2. **Then, run LLM enrichment** (for papers that need AI content):
   ```bash
   nohup python scripts/enrich_papers_llm.py --skip-existing > ../logs/enrichment_llm.log 2>&1 &
   ```

3. **Optionally, backfill DOI metadata** (for papers missing metadata):
   ```bash
   nohup python scripts/backfill_metadata_from_doi.py --skip-enriched > ../logs/enrichment_doi.log 2>&1 &
   ```

## Troubleshooting

### Script fails with "Connection refused"
- Check if LLM API is running: `curl http://192.168.1.81:1234/v1/models`
- Verify `FAST_LLM_API_BASE` in `.env`

### Script fails with database errors
- Check database connection: `psql -d bibliography_db -c "SELECT 1;"`
- Verify `DATABASE_URL` in `.env`

### Script is too slow
- Reduce `--batch-size` to avoid overwhelming the LLM API
- Check LLM API performance and resource usage

### Out of memory errors
- Reduce `--batch-size` further
- Process papers in smaller batches using `--limit`

## Example: Complete Enrichment Session

```bash
# SSH into server
ssh jforrest@mac-mini

# Navigate to backend
cd ~/production/hero-evidence-library/backend

# Activate virtual environment
source venv/bin/activate

# Start LLM enrichment in background
nohup python scripts/enrich_papers_llm.py --skip-existing --batch-size 5 > ../logs/enrichment_llm_$(date +%Y%m%d).log 2>&1 &

# Check it started
ps aux | grep enrich_papers_llm

# Monitor progress
tail -f ../logs/enrichment_llm_$(date +%Y%m%d).log
```
