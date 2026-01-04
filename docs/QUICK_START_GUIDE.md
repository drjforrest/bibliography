# HERO Evidence Library v2.0 - Quick Start Guide

## What We've Built

You now have a solid foundation for v2.0 with all the architectural pieces in place:

### ✅ Completed
1. **Separated Development Environment**
   - v1.0 remains untouched at `hero_evidence_library/`
   - v2.0 lives at `evidence_library_v2/`
   - Can run both simultaneously on different ports

2. **Updated Dependencies**
   - Added Celery, Redis, Kokoro TTS, Docling
   - Upgraded LangGraph and LiteLLM
   - All v2 features ready to implement

3. **Database Models**
   - `Podcast`: Store generated podcasts with metadata
   - `Summary`: Multiple summary types (lay, technical, executive)
   - `Infographic`: Visual content generation
   - `SlideDeck`: Presentation export
   - All in `backend/app/v2_models.py`

4. **Celery Infrastructure**
   - Configured in `backend/celery_app.py`
   - Separate queues for podcasts and summaries
   - Flower monitoring ready

5. **Podcaster Agent (Partial)**
   - Configuration, State, Prompts, Utils complete
   - Adapted specifically for academic content
   - Ready for graph and nodes implementation

---

## Next: Immediate Action Items

### Option A: Continue Building (Recommended)

**Next file to create**: `backend/app/agents/podcaster/nodes.py`

This is the core logic that:
1. Takes research paper content
2. Generates podcast transcript via LLM
3. Converts to speech via TTS
4. Merges audio files into final podcast

I can port this from SurfSense with HERO adaptations if you'd like to continue now.

**After nodes.py**, you'll need:
- `graph.py` - LangGraph workflow
- `__init__.py` - Module exports
- Service modules for LLM and TTS
- Celery task wrapper
- API routes

### Option B: Test Foundation First

Before adding more complexity, you could:

1. **Install dependencies**:
```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/backend
pip install -e .
```

2. **Set up Redis**:
```bash
brew install redis
brew services start redis
```

3. **Test Celery**:
```bash
celery -A celery_app worker --loglevel=info
```

4. **Run backend**:
```bash
uvicorn main:app --reload --port 8001
```

---

## Key Files Reference

### Documentation
- `docs/V2_MIGRATION_PLAN.md` - Overall strategy and architecture
- `docs/IMPLEMENTATION_ROADMAP.md` - Detailed task breakdown with timeline
- `docs/QUICK_START_GUIDE.md` - This file

### Code Structure
```
evidence_library_v2/
├── backend/
│   ├── celery_app.py                    # ✅ Celery configuration
│   ├── pyproject.toml                   # ✅ Updated dependencies
│   └── app/
│       ├── v2_models.py                 # ✅ New database models
│       └── agents/
│           └── podcaster/
│               ├── configuration.py     # ✅ Runtime config
│               ├── state.py             # ✅ State models
│               ├── prompts.py           # ✅ Academic prompts
│               ├── utils.py             # ✅ Helper functions
│               ├── nodes.py             # ⏳ NEXT: Core logic
│               ├── graph.py             # ⏳ LangGraph workflow
│               └── __init__.py          # ⏳ Module exports
```

---

## Design Decisions Made

### 1. Academic Podcast Style
The prompts are designed to create podcasts where:
- Two hosts discuss research (not narrator + interviewer)
- Specific findings and methods are referenced
- Scientific accuracy is paramount
- Natural conversation flow with follow-up questions
- Accessible but rigorous explanation

Example exchange from prompts:
> Host 1: "That's a substantial sample size. And how did they measure efficacy?"
> Host 2: "They used two metrics: neutralizing antibody titers and breakthrough infection rates..."

### 2. Flexible Configuration
Users can customize:
- Podcast style (conversational, formal, educational)
- Length (short: 5min, medium: 10min, long: 15min+)
- Custom instructions (tone, focus areas, audience level)

### 3. Extensible Architecture
The structure supports adding:
- Summary generation (same pattern as podcasts)
- Infographic creation (visual outputs)
- Slide deck export (presentation formats)

All using Celery for background processing.

---

## Questions for You

Before I continue building, a few strategic questions:

### 1. TTS Provider Preference?
- **OpenAI TTS**: Easiest to set up, high quality, ~$15 per 1M characters
- **Kokoro (local)**: Free, runs locally, requires GPU for best performance
- **Recommendation**: Start with OpenAI, optimize later if needed

### 2. Database Strategy?
- **Option A**: Create new v2 database (safer, cleaner)
- **Option B**: Add tables to v1 database (easier eventual merge)
- **Recommendation**: New database initially, merge after testing

### 3. Development Priority?
What's more valuable to you right now:
- **Complete podcaster** (full working podcast generation)
- **Test foundation** (ensure Celery, Redis, basic flow works)
- **Database setup** (run migrations, integrate models)

### 4. Voice Selection?
For the two podcast hosts:
- Should both be Canadian English?
- Preference for voice characteristics (warm, professional, casual)?
- Gender diversity preference?

---

## What Makes This Exciting

This isn't just adding features - it's transforming how researchers interact with literature. Instead of:

**v1.0**: "Search papers → Read abstracts → Manual synthesis"

You get:

**v2.0**: "Search papers → Generate podcast → Listen while walking/driving → Get structured summaries → Export slides for presentation"

The SurfSense codebase gives you battle-tested infrastructure for this, and your academic focus means the content will be rigorous and valuable in ways generic AI tools can't match.

Think about it: a postdoc could select 5 recent papers on a topic, generate a 15-minute podcast discussion on their commute, and have a synthesized understanding before they even sit down to write. That's genuinely transformative.

---

## Ready to Continue?

Let me know if you want to:
1. **Keep building** - I'll port the nodes.py and graph.py modules next
2. **Test infrastructure** - I'll create setup scripts and test cases
3. **Plan further** - We can refine the roadmap or explore other features

The foundation is solid and v1 is completely safe. We're in a great position to move forward.

---

**Created**: 2025-01-04  
**Status**: Foundation Complete, Ready for Next Phase  
**Owner**: Jamie Forrest
