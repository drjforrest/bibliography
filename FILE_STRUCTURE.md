# HERO Evidence Library v2.0 - Complete File Structure

## ✅ Files Created

```
evidence_library_v2/
│
├── V2_SETUP_SUMMARY.md                    # Quick overview
│
├── docs/
│   ├── V2_MIGRATION_PLAN.md               # Strategic plan
│   ├── IMPLEMENTATION_ROADMAP.md          # Detailed tasks
│   └── QUICK_START_GUIDE.md               # Next steps
│
└── backend/
    ├── celery_app.py                      # Celery configuration
    ├── pyproject.toml                     # Updated dependencies (v2.0.0)
    │
    └── app/
        ├── v2_models.py                   # Database models:
        │                                  #   - Podcast
        │                                  #   - Summary  
        │                                  #   - Infographic
        │                                  #   - SlideDeck
        │
        └── agents/
            └── podcaster/
                ├── configuration.py       # Runtime config
                ├── state.py               # Pydantic state models
                ├── prompts.py             # Academic prompts
                └── utils.py               # Helper functions
```

## ⏳ Files To Create Next

```
backend/app/
│
├── agents/podcaster/
│   ├── __init__.py                        # Module exports
│   ├── nodes.py                           # Core logic (HIGH PRIORITY)
│   └── graph.py                           # LangGraph workflow (HIGH PRIORITY)
│
├── services/
│   ├── llm_service.py                     # Get LLM for search space
│   ├── kokoro_tts_service.py              # Local TTS engine
│   └── docling_service.py                 # Enhanced PDF processing
│
├── tasks/
│   └── podcast_tasks.py                   # Celery task wrapper
│
└── routes/
    ├── podcast_routes.py                  # API endpoints
    ├── summary_routes.py                  # Summary generation
    └── content_routes.py                  # Multi-modal content
```

## 📦 Installation Steps

### 1. Install Dependencies
```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend
pip install -e .
```

### 2. Set Up Redis
```bash
brew install redis
brew services start redis
```

### 3. Create Environment File
```bash
# backend/.env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
TTS_SERVICE=openai
TTS_SERVICE_API_KEY=your-openai-api-key
PODCAST_STORAGE_PATH=/Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/data/podcasts
```

### 4. Create Podcast Directory
```bash
mkdir -p /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/data/podcasts
```

## 🚀 Running v2 Development

```bash
# Terminal 1: Redis (if not running as service)
redis-server

# Terminal 2: Celery Worker
cd backend
celery -A celery_app worker --loglevel=info

# Terminal 3: Celery Flower (optional monitoring)
celery -A celery_app flower --port=5555

# Terminal 4: Backend Server
uvicorn main:app --reload --port 8001

# Terminal 5: Frontend (when ready)
cd frontend/nextjs-app
npm run dev -- --port 3001
```

## 📊 Monitoring URLs

- Backend API: http://localhost:8001/docs
- Celery Flower: http://localhost:5555
- Frontend: http://localhost:3001

## 🔄 Parallel Development

v1 and v2 can run simultaneously:

```bash
# v1.0 (production)
Port 8000 (backend)
Port 3000 (frontend)

# v2.0 (development)
Port 8001 (backend)
Port 3001 (frontend)
```

## 📝 Key Documentation

1. **Quick Start**: `docs/QUICK_START_GUIDE.md`
2. **Strategy**: `docs/V2_MIGRATION_PLAN.md`
3. **Tasks**: `docs/IMPLEMENTATION_ROADMAP.md`
4. **Overview**: `V2_SETUP_SUMMARY.md` (this directory)

## 🎯 What's Working

- ✅ Separated development environment
- ✅ Updated dependencies (Celery, Redis, Kokoro, Docling)
- ✅ Database models designed
- ✅ Celery infrastructure configured
- ✅ Podcaster agent foundation (config, state, prompts, utils)
- ✅ Academic-focused prompts
- ✅ Comprehensive documentation

## 🎯 What's Next

1. Port `nodes.py` from SurfSense (transcript generation, TTS, audio merging)
2. Create `graph.py` (LangGraph workflow)
3. Add service modules (LLM, TTS)
4. Create Celery task wrapper
5. Build API routes
6. Run database migration
7. Test end-to-end

## 🤝 Ready to Continue

The foundation is solid. You can now:
- Install dependencies and test infrastructure
- Continue building (port nodes.py and graph.py)
- Review documentation and plan next steps

Everything is set up to keep v1 completely safe while building v2.

---

**Status**: Foundation Complete  
**Created**: 2025-01-04  
**Next**: Port core podcaster modules
