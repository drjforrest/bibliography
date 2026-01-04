# Simplified v2.0 Service Architecture (Using OpenRouter)

## Service Provision Model

### User-Provided Keys (2 total)

#### 1. OpenRouter API Key (Already Have) ✅
**Provides Access To**:
- OpenAI: GPT-4, GPT-4o, GPT-4o-mini, GPT-3.5
- Anthropic: Claude Sonnet 4, Opus 3.5, Haiku
- Google: Gemini Pro, Gemini Flash
- Meta: Llama 3.1, Llama 3.2
- Mistral: Large, Medium, Small
- And 100+ other models

**Used For**:
- Podcast transcript generation
- Summary generation (all types)
- Any LLM-powered feature

**Cost**: Pay-as-you-go directly to OpenRouter
**Storage**: `user.openrouter_api_key` (already exists)

#### 2. ElevenLabs API Key (New, Optional)
**Provides Access To**:
- Premium voice synthesis
- Emotional voice control
- Voice cloning
- Multi-language support

**Used For**:
- Premium podcast voices (upgrade from Kokoro)
- Custom voice creation

**Cost**: 
- Free tier: 10,000 chars/month
- Creator: $5/month (30,000 chars)
- Pro: $22/month (100,000 chars)

**Storage**: `user.elevenlabs_api_key` (need to add)

---

### Centralized Services (No Keys Required)

#### 1. Kokoro TTS (Default) ✅
- Free, local, open-source
- Good quality for research podcasts
- No API key needed
- GPU-accelerated on your server

#### 2. OpenAI TTS (Via OpenRouter Key)
- If user has OpenRouter key
- Can route TTS through OpenRouter
- $15/1M characters
- Simple upgrade from Kokoro

---

## User Table Changes Needed

```sql
-- Add to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS elevenlabs_api_key VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS default_tts_provider VARCHAR(50) DEFAULT 'kokoro';

-- Options for default_tts_provider:
-- 'kokoro' (free, default)
-- 'openai' (via OpenRouter)
-- 'elevenlabs' (requires elevenlabs_api_key)
```

---

## LLM Service Implementation

### Current v1 Pattern (Keep This)
```python
# app/services/llm_service.py

async def get_llm_for_search_space(search_space: SearchSpace) -> BaseChatModel:
    """Get LLM based on user's OpenRouter key."""
    user = search_space.user
    
    if user.openrouter_api_key:
        return ChatOpenAI(
            model=search_space.llm_model or "openai/gpt-4o-mini",
            api_key=user.decrypted_openrouter_key,
            base_url="https://openrouter.ai/api/v1"
        )
    else:
        raise ValueError("OpenRouter API key required")
```

### v2 Extension (For Podcasts)
```python
# app/services/podcast_llm_service.py

async def get_podcast_llm(user: User, model_preference: str = None) -> BaseChatModel:
    """
    Get LLM for podcast generation.
    
    Args:
        user: User with OpenRouter key
        model_preference: Optional model override (e.g., "anthropic/claude-sonnet-4")
    
    Returns:
        Configured LLM for podcast generation
    
    Raises:
        ValueError: If no OpenRouter key
    """
    if not user.openrouter_api_key:
        raise ValueError("OpenRouter API key required for podcast generation")
    
    # Default to good podcast model (balance cost/quality)
    default_model = "anthropic/claude-sonnet-4"  # $3/M input, $15/M output
    # or "openai/gpt-4o-mini"  # $0.15/M input, $0.60/M output (cheaper)
    
    model = model_preference or default_model
    
    return ChatOpenAI(
        model=model,
        api_key=user.decrypted_openrouter_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.7,  # More creative for podcast dialogue
        max_tokens=8000   # Long enough for full transcript
    )
```

---

## TTS Service Implementation

```python
# app/services/tts_service.py

from enum import Enum
from typing import List, BinaryIO

class TTSProvider(str, Enum):
    KOKORO = "kokoro"
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"

class TTSService:
    """Unified TTS service supporting multiple providers."""
    
    def __init__(self, user: User):
        self.user = user
        self.provider = user.default_tts_provider or TTSProvider.KOKORO
    
    async def synthesize(
        self, 
        text: str, 
        voice_id: str = "default",
        speaker: int = 0  # 0 or 1 for two-speaker podcast
    ) -> bytes:
        """
        Generate audio from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier (provider-specific)
            speaker: Speaker index (0=host1, 1=host2)
        
        Returns:
            Audio bytes (format depends on provider)
        """
        if self.provider == TTSProvider.KOKORO:
            return await self._kokoro_synthesize(text, speaker)
        
        elif self.provider == TTSProvider.OPENAI:
            return await self._openai_synthesize(text, voice_id)
        
        elif self.provider == TTSProvider.ELEVENLABS:
            return await self._elevenlabs_synthesize(text, voice_id)
        
        else:
            raise ValueError(f"Unknown TTS provider: {self.provider}")
    
    async def _kokoro_synthesize(self, text: str, speaker: int) -> bytes:
        """Use local Kokoro TTS (free)."""
        from kokoro import generate  # Your Kokoro integration
        
        # Map speaker to voice
        voice = "af_bella" if speaker == 0 else "am_michael"
        
        audio = generate(
            text=text,
            voice=voice,
            speed=1.0,
            lang="en-us"
        )
        
        return audio  # Returns WAV bytes
    
    async def _openai_synthesize(self, text: str, voice_id: str) -> bytes:
        """Use OpenAI TTS via OpenRouter key."""
        if not self.user.openrouter_api_key:
            raise ValueError("OpenRouter API key required for OpenAI TTS")
        
        # OpenAI TTS endpoint
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.user.decrypted_openrouter_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",  # or "tts-1-hd" for better quality
                    "voice": voice_id or "alloy",  # alloy, echo, fable, onyx, nova, shimmer
                    "input": text,
                    "speed": 1.0
                }
            )
            response.raise_for_status()
            return response.content  # Returns MP3 bytes
    
    async def _elevenlabs_synthesize(self, text: str, voice_id: str) -> bytes:
        """Use ElevenLabs TTS (premium)."""
        if not self.user.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key required")
        
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.user.decrypted_elevenlabs_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
            )
            response.raise_for_status()
            return response.content  # Returns MP3 bytes
```

---

## Settings UI (Simplified)

```typescript
// Profile → API Keys

interface UserAPIKeys {
  openrouter_api_key: string | null;
  elevenlabs_api_key: string | null;
  default_tts_provider: 'kokoro' | 'openai' | 'elevenlabs';
}

// UI Component
<Card title="AI Service Configuration">
  
  {/* Already exists in v1 */}
  <FormField
    label="OpenRouter API Key"
    value={user.openrouter_api_key}
    type="password"
    help="One key for 100+ LLMs (GPT-4, Claude, Gemini, etc.)"
  />
  
  {/* New for v2 */}
  <FormField
    label="ElevenLabs API Key (Optional)"
    value={user.elevenlabs_api_key}
    type="password"
    help="Premium voices for podcasts"
  />
  
  <FormField
    label="Default Voice Provider"
    value={user.default_tts_provider}
    type="select"
    options={[
      { value: 'kokoro', label: 'Kokoro (Free)' },
      { value: 'openai', label: 'OpenAI TTS (Requires OpenRouter key)' },
      { value: 'elevenlabs', label: 'ElevenLabs (Premium)' }
    ]}
  />
  
</Card>
```

---

## Podcast Generation Flow

```python
# app/tasks/podcast_tasks.py

from celery import shared_task

@shared_task
async def generate_podcast_task(podcast_id: int):
    """Background task for podcast generation."""
    
    async with get_async_session_context() as session:
        # Get podcast and user
        podcast = await session.get(Podcast, podcast_id)
        user = podcast.user
        
        # 1. Get LLM (via OpenRouter)
        llm = await get_podcast_llm(user)
        
        # 2. Load papers
        papers = await load_papers(podcast.source_paper_ids, session)
        
        # 3. Generate transcript
        from app.agents.podcaster.graph import create_podcast_graph
        graph = create_podcast_graph(llm)
        
        result = await graph.ainvoke({
            "papers": papers,
            "user_prompt": podcast.user_prompt,
            "title": podcast.title
        })
        
        transcript = result["podcast_transcripts"]  # List[PodcastTranscriptEntry]
        
        # 4. Generate audio with TTS
        tts_service = TTSService(user)
        audio_segments = []
        
        for entry in transcript:
            audio_bytes = await tts_service.synthesize(
                text=entry.dialog,
                speaker=entry.speaker_id
            )
            audio_segments.append(audio_bytes)
        
        # 5. Merge audio with FFmpeg
        final_audio = await merge_audio_segments(audio_segments)
        
        # 6. Save to storage
        file_location = await save_podcast_audio(podcast_id, final_audio)
        
        # 7. Update podcast record
        podcast.podcast_transcript = [e.dict() for e in transcript]
        podcast.file_location = file_location
        podcast.file_size_bytes = len(final_audio)
        podcast.duration_seconds = estimate_duration(transcript)
        podcast.generation_status = "complete"
        
        await session.commit()
```

---

## Cost Estimates (Using OpenRouter)

### Transcript Generation
**Model**: `anthropic/claude-sonnet-4`
- Input: ~20k tokens (paper context) × $3/M = $0.06
- Output: ~5k tokens (transcript) × $15/M = $0.075
- **Total**: ~$0.135 per podcast

**Model**: `openai/gpt-4o-mini` (cheaper alternative)
- Input: ~20k tokens × $0.15/M = $0.003
- Output: ~5k tokens × $0.60/M = $0.003
- **Total**: ~$0.006 per podcast (23x cheaper!)

### TTS Generation
**Kokoro** (default): FREE
**OpenAI TTS**: ~3,000 chars × $15/1M = $0.045
**ElevenLabs**: ~3,000 chars × $22/100k = $0.66

### Example Costs
1. **Budget**: GPT-4o-mini + Kokoro = $0.006
2. **Balanced**: Claude Sonnet + Kokoro = $0.135
3. **Premium**: Claude Sonnet + ElevenLabs = $0.80

All costs paid directly by user to providers ✅

---

## Implementation Checklist

### Database Changes
- [ ] Add `elevenlabs_api_key` column to user table
- [ ] Add `default_tts_provider` column to user table
- [ ] Add encryption for ElevenLabs key (same as OpenRouter)

### Backend Services
- [ ] Create `TTSService` class with multi-provider support
- [ ] Integrate Kokoro TTS
- [ ] Add OpenAI TTS via OpenRouter key
- [ ] Add ElevenLabs TTS support
- [ ] Update `get_podcast_llm()` to use OpenRouter

### Frontend UI
- [ ] Add ElevenLabs API key field to settings
- [ ] Add TTS provider selector
- [ ] Show voice preview for each provider
- [ ] Display cost estimates in generation modal

### Documentation
- [ ] Update user guide with OpenRouter setup
- [ ] Document TTS provider options
- [ ] Add cost comparison table
- [ ] Create API key management guide

---

## Key Advantages of OpenRouter Approach

1. **One Key, Many Models**: User maintains one key instead of 3-4
2. **Unified Billing**: One invoice from OpenRouter
3. **Model Flexibility**: Easy to switch between GPT-4, Claude, Gemini
4. **Cost Optimization**: Compare prices across providers in real-time
5. **Fallback Logic**: If one model is down, automatically try another

---

**Created**: 2025-01-04  
**Status**: Ready to implement  
**Complexity**: Low (minimal new infrastructure)
