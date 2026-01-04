# HERO Evidence Library v2.0 - Implementation Roadmap

## Status: Foundation Complete ✅

### What's Been Done

#### 1. Project Setup
- ✅ Created separate v2 repository at `evidence_library_v2/`
- ✅ Updated `pyproject.toml` with v2.0 dependencies
- ✅ Created comprehensive migration plan documentation

#### 2. Infrastructure
- ✅ Configured Celery app for background tasks
- ✅ Defined v2.0 database models (Podcast, Summary, Infographic, SlideDeck)
- ✅ Created podcaster agent directory structure

#### 3. Podcaster Module (Partial)
- ✅ Configuration module for runtime parameters
- ✅ State management with Pydantic models
- ✅ Academic-focused prompts for scientific content
- ✅ Utility functions (voice selection, validation)
- ⏳ Nodes module (transcript generation, TTS, audio merging)
- ⏳ Graph module (LangGraph workflow)
- ⏳ __init__.py files

---

## Next Steps - Critical Path

### Phase 1: Complete Podcaster Module (Next 1-2 days)

#### 1.1 Finish Core Modules
```bash
# Still needed:
backend/app/agents/podcaster/
├── __init__.py           # Export main functions
├── graph.py              # LangGraph workflow definition
└── nodes.py              # Transcript generation, TTS, audio merging
```

**Dependencies**: 
- Read SurfSense nodes.py and graph.py
- Adapt for HERO's database models
- Configure LLM service integration

#### 1.2 Create Service Modules
```bash
backend/app/services/
├── kokoro_tts_service.py     # Local TTS engine
├── llm_service.py            # Get LLM for search space
└── docling_service.py        # Enhanced PDF processing
```

#### 1.3 Create Celery Task
```bash
backend/app/tasks/
└── podcast_tasks.py          # Background podcast generation
```

### Phase 2: Database Integration (Next 2-3 days)

#### 2.1 Create Alembic Migration
```bash
# Generate migration for v2 models
cd backend
alembic revision --autogenerate -m "Add v2.0 content generation tables"
alembic upgrade head
```

#### 2.2 Update Existing Models
Add relationships to `backend/app/db.py`:
```python
# In SearchSpace class:
podcasts = relationship("Podcast", ...)
summaries = relationship("Summary", ...)
infographics = relationship("Infographic", ...)
slide_decks = relationship("SlideDeck", ...)

# In User class:
podcasts = relationship("Podcast", ...)
# ... etc
```

#### 2.3 Import v2 Models
In `backend/app/db.py`:
```python
from app.v2_models import (
    Podcast,
    Summary,
    SummaryType,
    Infographic,
    SlideDeck
)
```

### Phase 3: API Routes (Next 2-3 days)

#### 3.1 Podcast Routes
```bash
backend/app/routes/podcast_routes.py
```

Endpoints needed:
- `POST /api/podcasts/generate` - Start podcast generation
- `GET /api/podcasts/{task_id}/status` - Poll generation status
- `GET /api/podcasts/{podcast_id}` - Get podcast details
- `GET /api/podcasts` - List user's podcasts
- `DELETE /api/podcasts/{podcast_id}` - Delete podcast
- `GET /api/podcasts/{podcast_id}/download` - Download audio file

#### 3.2 Integration with Main App
Update `backend/app/app.py`:
```python
from app.routes import podcast_routes

app.include_router(
    podcast_routes.router, 
    prefix="/api", 
    tags=["podcasts"]
)
```

### Phase 4: Environment Setup (Next 1 day)

#### 4.1 Create `.env` Variables
```bash
# Add to backend/.env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# TTS Configuration
TTS_SERVICE=openai  # or local/kokoro
TTS_SERVICE_API_KEY=your-openai-key
TTS_SERVICE_API_BASE=https://api.openai.com/v1

# Storage
PODCAST_STORAGE_PATH=/Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/data/podcasts
```

#### 4.2 Install Infrastructure
```bash
# Install Redis
brew install redis
brew services start redis

# Create podcast directory
mkdir -p /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/data/podcasts

# Install FFmpeg (if not already installed)
brew install ffmpeg
```

#### 4.3 Install Python Dependencies
```bash
cd backend
pip install -e .
# or with uv:
uv pip install -e .
```

### Phase 5: Testing (Ongoing)

#### 5.1 Unit Tests
```bash
backend/tests/
├── test_podcaster_graph.py
├── test_podcast_generation.py
└── test_podcast_tasks.py
```

#### 5.2 Integration Test
Create end-to-end test:
1. Select papers from database
2. Generate podcast via API
3. Poll for completion
4. Verify audio file exists
5. Check database entry

### Phase 6: Frontend Integration (Week 2-3)

#### 6.1 Paper Selection Component
```typescript
frontend/nextjs-app/components/
└── PodcastGenerator/
    ├── PaperSelector.tsx
    ├── GenerationOptions.tsx
    └── PodcastPlayer.tsx
```

#### 6.2 API Client
```typescript
frontend/nextjs-app/lib/
└── api/
    └── podcasts.ts
```

---

## Development Workflow

### Running v2 Development Environment

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend
celery -A celery_app worker --loglevel=info --queues=podcasts,summaries

# Terminal 3: Start Celery Flower (monitoring)
celery -A celery_app flower --port=5555

# Terminal 4: Start Backend
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend
uvicorn main:app --reload --port 8001

# Terminal 5: Start Frontend (when ready)
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/frontend/nextjs-app
npm run dev -- --port 3001
```

### Monitoring Tools

- **Celery Flower**: http://localhost:5555 - Monitor task queue
- **Backend API**: http://localhost:8001/docs - FastAPI Swagger UI
- **Frontend**: http://localhost:3001 - Next.js dev server

---

## Risk Mitigation

### Technical Risks

**Risk**: TTS quality varies across providers
**Mitigation**: Test with OpenAI first, then optimize with Kokoro for cost

**Risk**: Podcast generation takes >5 minutes
**Mitigation**: Implement progress updates, set user expectations

**Risk**: Audio file sizes too large
**Mitigation**: Use MP3 compression, consider streaming option

### Development Risks

**Risk**: Complexity leads to scope creep
**Mitigation**: Build podcast feature first, defer summaries/infographics to Phase 2

**Risk**: Database migration breaks v1
**Mitigation**: Use separate v2 database until stable, then merge

---

## Success Criteria

### Minimum Viable Product (MVP)
- [ ] User can select 1-3 papers
- [ ] System generates 5-10 minute podcast
- [ ] Audio file is downloadable
- [ ] Generation status is visible
- [ ] Podcast is saved to database

### Extended Goals
- [ ] Transcript synchronized with audio
- [ ] Multiple voice options
- [ ] Podcast length customization
- [ ] Style/tone options (formal vs. casual)
- [ ] Share/export functionality

---

## Timeline Estimate (Revised)

| Task | Duration | Completion Date |
|------|----------|-----------------|
| Complete podcaster modules | 1-2 days | Jan 6 |
| Database migration | 1 day | Jan 7 |
| API routes | 2-3 days | Jan 10 |
| Infrastructure setup | 1 day | Jan 7 |
| End-to-end testing | 2 days | Jan 12 |
| Frontend components | 4-5 days | Jan 17 |
| **MVP Complete** | **~2 weeks** | **Jan 17** |

---

## Questions to Resolve

1. **TTS Provider**: Start with OpenAI or Kokoro?
   - OpenAI: Easier, higher quality, costs money
   - Kokoro: Free, local, requires more setup

2. **Database**: Separate v2 DB or shared with v1?
   - Separate: Safer, cleaner development
   - Shared: Easier eventual merge

3. **Storage**: Local filesystem or S3?
   - Local: Simpler for development
   - S3: Better for production scaling

4. **Authentication**: Reuse v1 Clerk setup?
   - Yes: Seamless user experience
   - Need to verify JWT token sharing

---

**Last Updated**: 2025-01-04
**Status**: Foundation Complete, Ready for Implementation
**Owner**: Jamie Forrest
