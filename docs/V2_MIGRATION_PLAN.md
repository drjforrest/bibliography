# HERO Evidence Library v2.0 Migration Plan

## Vision
Transform the HERO Evidence Library from a static repository into a **Dynamic Learning Powerhouse** that can:
- Generate engaging podcasts from selected papers
- Create visual summaries and infographics
- Export formatted slide decks
- Provide multi-modal content synthesis

## Architecture Overview

### v1.0 → v2.0 Evolution
```
v1.0: Static Library               v2.0: Dynamic Learning Platform
├── Paper storage                  ├── Paper storage (unchanged)
├── Semantic search                ├── Enhanced semantic search
├── RAG-based Q&A                  ├── RAG-based Q&A (enhanced)
└── Manual synthesis               ├── Podcast generation (NEW)
                                   ├── Summary generation (NEW)
                                   ├── Infographic creation (NEW)
                                   └── Slide deck export (NEW)
```

### New Technology Stack Components
- **Celery + Redis**: Background task processing for long-running operations
- **Docling**: Advanced PDF parsing (tables, figures, structured content)
- **Kokoro TTS**: Local text-to-speech for podcast generation
- **FFmpeg**: Audio file merging and processing
- **LangGraph Checkpointing**: Persistent state for multi-step workflows

## Phase 1: Foundation Setup ✓ IN PROGRESS

### 1.1 Update Dependencies
**File**: `backend/pyproject.toml`

Added dependencies:
```toml
"celery[redis]>=5.5.3"           # Background task queue
"flower>=2.0.1"                   # Celery monitoring UI
"redis>=5.2.1"                    # Task state management
"docling>=2.15.0"                 # Advanced PDF processing
"kokoro>=0.9.4"                   # Local TTS engine
"soundfile>=0.13.1"               # Audio file handling
"python-ffmpeg>=2.0.12"           # Audio processing
"static-ffmpeg>=2.13"             # FFmpeg binary
"langgraph-checkpoint-postgres>=3.0.2"  # State persistence
"psycopg[binary,pool]>=3.3.2"    # PostgreSQL driver
"datasets>=2.21.0"                # Dataset handling
"pyarrow>=15.0.0,<19.0.0"        # Data serialization
```

### 1.2 Database Schema Extensions
**Status**: Migration scripts to be created

New tables:
- `podcasts`: Store generated podcasts with metadata
- `summaries`: AI-generated paper summaries
- `infographics`: Generated visual content
- `slide_decks`: Exported presentation files

### 1.3 Infrastructure Setup
- [ ] Install and configure Redis
- [ ] Set up Celery worker
- [ ] Configure Flower for monitoring
- [ ] Create podcast storage directory
- [ ] Set up FFmpeg

## Phase 2: Core Module Porting

### 2.1 Podcast Generation Module
**Source**: `SurfSense/surfsense_backend/app/agents/podcaster/`

Files to port:
```
backend/app/agents/podcaster/
├── __init__.py
├── graph.py              # LangGraph workflow
├── nodes.py              # Transcript generation, TTS, audio merging
├── prompts.py            # Scientific content adaptation
├── state.py              # Pydantic state models
├── configuration.py      # Runtime configuration
└── utils.py              # Voice selection, helpers
```

**Adaptations Required**:
1. Replace `search_space_id` references with HERO's model
2. Modify prompts for academic/scientific content
3. Point file storage to `/data/podcasts/`
4. Integrate with HERO's user authentication

### 2.2 Celery Integration
**New Files**:
```
backend/
├── celery_app.py         # Celery instance configuration
└── app/tasks/
    └── podcast_tasks.py  # Podcast generation tasks
```

### 2.3 Enhanced PDF Processing
**Source**: `SurfSense/surfsense_backend/app/services/docling_service.py`

Benefits:
- Extract tables as structured data
- Identify and extract figures
- Better heading/section detection
- Improved metadata extraction

### 2.4 API Routes
**New Files**:
```
backend/app/routes/
├── podcast_routes.py     # Podcast CRUD and generation
├── summary_routes.py     # Summary generation endpoints
└── content_routes.py     # Multi-modal content generation
```

## Phase 3: Frontend Integration

### 3.1 Paper Selection UI
- Multi-select component for choosing papers
- Preview selected papers with metadata
- Configure generation options (tone, length, style)

### 3.2 Task Polling & Progress
- WebSocket or polling-based progress updates
- Visual feedback during generation
- Cancellation support

### 3.3 Content Viewers
- Audio player for podcasts with transcript sync
- PDF viewer for generated summaries
- Slide deck preview/download

## Development Workflow

### Environment Separation
```bash
# v1.0 (production)
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
uvicorn backend.main:app --port 8000

# v2.0 (development)
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
uvicorn backend.main:app --port 8001
```

### Database Strategy
- **Option 1**: Separate v2 database for clean development
- **Option 2**: Shared database with feature flags
- **Recommendation**: Separate database initially, merge after testing

### Git Strategy
```bash
# Create v2 development branch
git checkout -b feature/v2-podcast-generation

# Keep v1 main branch stable
git checkout main  # v1.0 stable
```

## Timeline Estimate

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Foundation | 1-2 weeks | Dependencies, DB schema, infra |
| 2. Podcast Module | 2-3 weeks | Working podcast generation |
| 3. Frontend | 1-2 weeks | UI for content generation |
| 4. Advanced Features | 2-3 weeks | Summaries, infographics, slides |
| **Total** | **6-10 weeks** | Full v2.0 release |

---

**Document Status**: Living document, updated as implementation progresses
**Last Updated**: 2025-01-04
**Owner**: Jamie Forrest
**Version**: 1.0
