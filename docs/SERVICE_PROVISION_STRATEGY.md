# v2.0 Service Provision Strategy - User vs Centralized

## Overview

For podcast generation and content synthesis, we need to decide which AI services should be:
1. **User-provided** (keys stored in user table, user pays directly)
2. **Centralized** (HERO pays, included in subscription/free tier)

---

## Service Breakdown

### 1. LLM for Transcript Generation

**What it does**: Generates the podcast dialogue between two AI hosts discussing papers

**Options**:
- OpenAI GPT-4o/GPT-4o-mini
- Anthropic Claude (Sonnet, Haiku)
- Google Gemini
- Local models (Ollama, LM Studio)

**Recommendation: USER-PROVIDED** ✅

**Why**:
- **High token usage**: A 10-minute podcast = ~5,000 output tokens + paper context (~20k tokens) = ~$0.25-1.00 per podcast
- **Volume unpredictable**: Power users might generate 10+ podcasts/day = $10/day
- **User choice matters**: Some users prefer Claude (better reasoning), others GPT-4 (faster), others local (privacy)
- **Cost transparency**: Users see exactly what they're paying

**Implementation**:
```python
# User table already has these
user.openai_api_key
user.anthropic_api_key
# Could add:
user.google_api_key
user.default_llm_provider  # "openai" | "anthropic" | "google" | "local"
```

**Fallback**: If user has no key, offer "Try with your API key" prompt

---

### 2. Text-to-Speech (TTS)

**What it does**: Converts transcript text to audio (two voices for two hosts)

**Options**:

#### A. OpenAI TTS
- **Cost**: $15/1M characters (~$0.015 per podcast)
- **Quality**: Excellent, natural voices
- **Voices**: 6 options (alloy, echo, fable, onyx, nova, shimmer)
- **Speed**: Fast API
- **Recommendation**: **USER-PROVIDED** ✅

#### B. ElevenLabs
- **Cost**: $5/month (30k chars), $22/month (100k chars), $99/month (500k chars)
- **Quality**: Best-in-class, emotional range
- **Voices**: Highly customizable
- **Speed**: Good
- **Recommendation**: **USER-PROVIDED** ✅

#### C. Kokoro (Local/Free)
- **Cost**: FREE (runs locally)
- **Quality**: Good, improving
- **Voices**: Limited but growing
- **Speed**: Depends on GPU
- **Recommendation**: **DEFAULT OPTION** ⭐ (no key required)

#### D. Google Cloud TTS / AWS Polly
- **Cost**: ~$4/1M characters
- **Quality**: Good
- **Recommendation**: **USER-PROVIDED** (if they prefer)

**Strategy**:
```
Priority Order:
1. Kokoro (local) - FREE, no key required
2. OpenAI TTS - if user provides openai_api_key
3. ElevenLabs - if user provides elevenlabs_api_key
```

**Why Kokoro as Default**:
- Zero marginal cost
- Privacy (local processing)
- No rate limits
- "Good enough" for research podcasts
- Can upgrade to premium voices if desired

---

### 3. PDF Processing (Docling)

**What it does**: Extracts clean text/tables from PDFs for LLM consumption

**Recommendation: CENTRALIZED** 🏢

**Why**:
- **No API key needed**: Docling is open-source library
- **Compute-bound**: Runs on your infrastructure
- **Already doing it**: v1 already processes PDFs
- **One-time cost**: Process paper once, cache forever

**Implementation**: Already in v1, extend for v2

---

### 4. Audio Processing (FFmpeg)

**What it does**: Merges multiple TTS audio segments, adds effects, normalizes

**Recommendation: CENTRALIZED** 🏢

**Why**:
- **No API key needed**: FFmpeg is free software
- **Compute-bound**: Runs on your infrastructure
- **Lightweight**: Audio processing is fast
- **No marginal cost**: Just CPU cycles

---

### 5. Summary Generation LLM

**What it does**: Generates text summaries (lay, technical, executive, comparative)

**Recommendation: USER-PROVIDED** ✅

**Why**:
- Same reasoning as transcript generation
- High token usage for quality summaries
- User choice on model/style
- Cost transparency

**Reuse**: Same API keys as podcast generation

---

### 6. Infographic Generation

**What it does**: Creates visual diagrams from paper data

**Options**:

#### A. LLM → Structured Data → Rendering
- **LLM**: Extract key stats/findings → USER-PROVIDED ✅
- **Rendering**: Matplotlib/Plotly → CENTRALIZED 🏢

#### B. DALL-E / Midjourney / Stable Diffusion
- **Cost**: $0.04-0.10 per image
- **Recommendation**: USER-PROVIDED ✅ (optional premium feature)

---

### 7. Celery + Redis (Background Tasks)

**What it does**: Queues and processes long-running generation tasks

**Recommendation: CENTRALIZED** 🏢

**Why**:
- Infrastructure component
- No user configuration needed
- Part of platform reliability

---

## Summary Matrix

| Service | User-Provided? | Centralized? | Why |
|---------|---------------|--------------|-----|
| **LLM (Transcripts)** | ✅ | ❌ | High cost, user choice, volume unpredictable |
| **LLM (Summaries)** | ✅ | ❌ | Same as above |
| **OpenAI TTS** | ✅ | ❌ | Optional upgrade from free Kokoro |
| **ElevenLabs TTS** | ✅ | ❌ | Optional premium feature |
| **Kokoro TTS** | ❌ | ✅ | FREE default, no key needed |
| **Docling (PDF)** | ❌ | ✅ | Already centralized in v1 |
| **FFmpeg (Audio)** | ❌ | ✅ | Infrastructure, no cost |
| **Infographic Render** | ❌ | ✅ | Compute-bound, lightweight |
| **Image Gen (optional)** | ✅ | ❌ | Premium feature |
| **Celery/Redis** | ❌ | ✅ | Infrastructure |

---

## User Table Schema Extension

```python
class User(BaseModel):
    # Existing v1 keys
    openai_api_key = Column(String(255), nullable=True)
    
    # Add for v2
    anthropic_api_key = Column(String(255), nullable=True)
    google_api_key = Column(String(255), nullable=True)
    elevenlabs_api_key = Column(String(255), nullable=True)
    
    # Preferences
    default_llm_provider = Column(String(50), default="openai")  # openai|anthropic|google|local
    default_tts_provider = Column(String(50), default="kokoro")  # kokoro|openai|elevenlabs
    
    # Quota tracking (for free tier limits)
    monthly_podcast_count = Column(Integer, default=0)
    monthly_summary_count = Column(Integer, default=0)
    last_quota_reset = Column(TIMESTAMP(timezone=True), nullable=True)
```

---

## Cost Analysis

### Scenario 1: Free User (No API Keys)
- **Transcript**: Use local model (Ollama) or reject with "Add API key" message
- **TTS**: Kokoro (FREE)
- **Audio**: FFmpeg (FREE)
- **Total**: $0

### Scenario 2: Basic User (OpenAI Key Only)
- **Transcript**: GPT-4o-mini (~$0.25/podcast)
- **TTS**: Kokoro (FREE) or OpenAI TTS (+$0.015)
- **Audio**: FFmpeg (FREE)
- **Total**: ~$0.25/podcast (user pays OpenAI directly)

### Scenario 3: Power User (All Keys)
- **Transcript**: GPT-4 or Claude Sonnet (~$1.00/podcast)
- **TTS**: ElevenLabs (premium voices, ~$0.05/podcast)
- **Audio**: FFmpeg (FREE)
- **Total**: ~$1.05/podcast (user pays providers directly)

### HERO's Costs (Centralized)
- **Compute**: Kokoro TTS + FFmpeg (~$0.01/podcast in server costs)
- **Storage**: Audio files (~5MB each, ~$0.001/month/podcast in S3)
- **Celery/Redis**: Infrastructure (~$20/month flat)

---

## Free Tier Strategy

### Option A: Limited Free Generation
```
Free tier (no API keys):
- Use local Ollama model (slower but functional)
- Kokoro TTS
- 5 podcasts/month limit
- "Upgrade with your API key for unlimited generation"
```

### Option B: Hybrid Approach
```
Free tier:
- Use your API key for unlimited
- Or use HERO credits: 3 free podcasts/month
- Each podcast uses 1 HERO credit
- More credits = $5/month subscription
```

### Option C: Pure BYOK (Bring Your Own Key)
```
No free tier for generation:
- Must provide OpenAI/Anthropic API key
- Get unlimited generation (you pay provider)
- Kokoro TTS always free
- HERO never sees your usage costs
```

**Recommendation**: **Option C (Pure BYOK)** ✅

**Why**:
- Cleanest model: you pay for what you use
- No quota management complexity
- No subscription tiers needed for generation
- Users already comfortable with API keys (they're researchers)
- Positions HERO as infrastructure, not a reseller

---

## Implementation Strategy

### Phase 1: Core (Now)
1. Add `anthropic_api_key` to user table
2. Implement Kokoro TTS (free default)
3. Add LLM provider selection in generation request
4. Support OpenAI and Anthropic initially

### Phase 2: Premium TTS (Later)
1. Add `elevenlabs_api_key` to user table
2. Implement ElevenLabs integration
3. Add OpenAI TTS option
4. Let users choose voice/provider

### Phase 3: Local Models (Later)
1. Add Ollama/LM Studio support
2. Let users connect to local LLM servers
3. Privacy-focused researchers love this

---

## UI/UX Implications

### Settings Page (Profile → API Keys)
```
┌─────────────────────────────────────────┐
│ AI Service Configuration                │
├─────────────────────────────────────────┤
│                                         │
│ OpenAI API Key                          │
│ [sk-proj-...] ✓ Valid                  │
│                                         │
│ Anthropic API Key (Optional)            │
│ [Add key...] For Claude models          │
│                                         │
│ ElevenLabs API Key (Optional)           │
│ [Add key...] For premium voices         │
│                                         │
│ Default LLM Provider                     │
│ ○ OpenAI  ● Anthropic  ○ Local         │
│                                         │
│ Default Voice Provider                   │
│ ● Kokoro (Free)  ○ OpenAI  ○ ElevenLabs│
│                                         │
└─────────────────────────────────────────┘
```

### Podcast Generation Modal
```
┌─────────────────────────────────────────┐
│ Generate Podcast                        │
├─────────────────────────────────────────┤
│ Selected Papers: 3                      │
│                                         │
│ Model: [Claude Sonnet 4 ▼]             │
│   • Your API key will be used           │
│   • Est. cost: ~$0.75                   │
│                                         │
│ Voices: [Kokoro (Free) ▼]              │
│   • No additional cost                  │
│                                         │
│ [Generate Podcast]                      │
│                                         │
│ ⓘ Using your Anthropic API key         │
└─────────────────────────────────────────┘
```

---

## Competitive Positioning

### vs NotebookLM (Free but Google-powered)
- **NotebookLM**: Free, locked to Google's models
- **HERO**: BYOK, model choice, open-source TTS option
- **Advantage**: Privacy, flexibility, no vendor lock-in

### vs Perplexity (Subscription)
- **Perplexity**: $20/month unlimited
- **HERO**: Pay-as-you-go via your API key
- **Advantage**: Cost transparency, no subscription if low usage

### vs Elicit/Consensus (Per-paper pricing)
- **Elicit**: Credits per query
- **HERO**: BYOK, unlimited if you have API key
- **Advantage**: No artificial limits, researcher-friendly

---

## Security Considerations

### API Key Storage
```python
# Encrypt keys at rest
from cryptography.fernet import Fernet

# In User model
@property
def decrypted_openai_key(self):
    if not self.openai_api_key:
        return None
    return decrypt_api_key(self.openai_api_key)

# Never log keys
# Never send keys to frontend
# Rotate encryption key regularly
```

### Rate Limiting
```python
# Protect against abuse even with user keys
@rate_limit(max_requests=10, window=3600)  # 10 podcasts/hour
async def generate_podcast(user_id, paper_ids):
    ...
```

---

## Recommendation Summary

### User-Provided Keys (Store in User Table) ✅
1. **OpenAI API Key** - Already have
2. **Anthropic API Key** - Add now
3. **ElevenLabs API Key** - Add phase 2
4. **Google API Key** - Add phase 3

### Centralized Services (HERO Infrastructure) 🏢
1. **Kokoro TTS** - Free default
2. **FFmpeg** - Audio processing
3. **Docling** - PDF extraction (already have)
4. **Celery/Redis** - Task queue

### Business Model
- **BYOK (Bring Your Own Key)** primary model
- No generation limits with user keys
- Optional: 3 free credits/month using HERO's keys
- Optional: $5/month for 20 additional HERO credits
- **Focus**: Platform value, not reselling API access

---

## Next Steps

1. **Add `anthropic_api_key` column to user table**
2. **Implement LLM service selection logic**
3. **Set up Kokoro TTS integration**
4. **Build settings UI for key management**
5. **Document cost estimates for users**

---

**Created**: 2025-01-04
**Status**: Strategic Decision Required
**Recommendation**: User-provided LLM keys, centralized Kokoro TTS
