# Smart TTS Cost Optimization Strategy

## Concept: Auto-Select Cheapest TTS Based on Usage

Instead of users choosing between OpenAI and ElevenLabs, HERO automatically selects the most cost-effective option based on their usage patterns.

---

## How It Works

### Month 1: Discovery Phase (Free)
```
User generates podcasts with Kokoro (free)
HERO tracks: podcast count, character usage
```

### Month 2+: Smart Recommendation
```
Based on last month's usage, recommend:
- Low usage (1-6 podcasts): "Use OpenAI TTS - pay only $0.27/month"
- Medium usage (7-15 podcasts): "ElevenLabs Creator - $5/month is better"
- High usage (16+ podcasts): "ElevenLabs Pro - $22/month unlimited"
```

### Auto-Optimization (Optional)
```
If user provides BOTH keys:
- Calculate cost each month based on usage
- Automatically use cheaper option
- Show savings: "Saved $12 this month by using OpenAI"
```

---

## Implementation

### Database Schema
```sql
ALTER TABLE "user" ADD COLUMN openai_api_key VARCHAR(255);
ALTER TABLE "user" ADD COLUMN elevenlabs_api_key VARCHAR(255);
ALTER TABLE "user" ADD COLUMN tts_optimization_mode VARCHAR(50) DEFAULT 'auto';
-- Options: 'auto' | 'prefer_openai' | 'prefer_elevenlabs' | 'kokoro_only'

-- Usage tracking
CREATE TABLE podcast_usage_stats (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    month DATE NOT NULL,  -- First day of month
    podcast_count INTEGER DEFAULT 0,
    total_characters INTEGER DEFAULT 0,
    kokoro_count INTEGER DEFAULT 0,
    openai_count INTEGER DEFAULT 0,
    elevenlabs_count INTEGER DEFAULT 0,
    estimated_openai_cost DECIMAL(10,4),
    estimated_elevenlabs_cost DECIMAL(10,4),
    UNIQUE(user_id, month)
);
```

### Smart TTS Selector Service
```python
# app/services/smart_tts_service.py

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class SmartTTSService:
    """Automatically selects most cost-effective TTS provider."""
    
    # Pricing constants
    OPENAI_COST_PER_CHAR = Decimal("0.000015")  # $15/1M chars
    ELEVENLABS_FREE_CHARS = 10000
    ELEVENLABS_CREATOR_PRICE = Decimal("5.00")
    ELEVENLABS_CREATOR_CHARS = 30000
    ELEVENLABS_PRO_PRICE = Decimal("22.00")
    ELEVENLABS_PRO_CHARS = 100000
    
    def __init__(self, user: User, session: AsyncSession):
        self.user = user
        self.session = session
    
    async def get_optimal_provider(self, estimated_chars: int = 3000) -> str:
        """
        Determine optimal TTS provider based on usage and available keys.
        
        Returns: 'kokoro' | 'openai' | 'elevenlabs'
        """
        
        # Check what keys user has
        has_openai = bool(self.user.openai_api_key)
        has_elevenlabs = bool(self.user.elevenlabs_api_key)
        
        # If no premium keys, use Kokoro
        if not has_openai and not has_elevenlabs:
            return 'kokoro'
        
        # If user prefers specific provider, respect that
        if self.user.tts_optimization_mode == 'prefer_openai' and has_openai:
            return 'openai'
        if self.user.tts_optimization_mode == 'prefer_elevenlabs' and has_elevenlabs:
            return 'elevenlabs'
        if self.user.tts_optimization_mode == 'kokoro_only':
            return 'kokoro'
        
        # Auto mode: calculate based on this month's projected usage
        if self.user.tts_optimization_mode == 'auto':
            if has_openai and has_elevenlabs:
                # Both keys available - choose cheaper option
                return await self._choose_cheaper_provider(estimated_chars)
            elif has_openai:
                return 'openai'
            elif has_elevenlabs:
                return 'elevenlabs'
        
        # Fallback to free
        return 'kokoro'
    
    async def _choose_cheaper_provider(self, estimated_chars: int) -> str:
        """Compare costs and choose cheaper option."""
        
        # Get current month's usage so far
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.session.execute(
            select(PodcastUsageStats)
            .where(
                PodcastUsageStats.user_id == self.user.id,
                PodcastUsageStats.month == current_month
            )
        )
        stats = result.scalar_one_or_none()
        
        current_chars = stats.total_characters if stats else 0
        projected_chars = current_chars + estimated_chars
        
        # Calculate costs
        openai_cost = self._calculate_openai_cost(projected_chars)
        elevenlabs_cost = self._calculate_elevenlabs_cost(projected_chars)
        
        # Return cheaper option
        return 'openai' if openai_cost < elevenlabs_cost else 'elevenlabs'
    
    def _calculate_openai_cost(self, total_chars: int) -> Decimal:
        """Calculate OpenAI TTS cost."""
        return Decimal(total_chars) * self.OPENAI_COST_PER_CHAR
    
    def _calculate_elevenlabs_cost(self, total_chars: int) -> Decimal:
        """Calculate ElevenLabs subscription cost."""
        if total_chars <= self.ELEVENLABS_FREE_CHARS:
            return Decimal("0.00")
        elif total_chars <= self.ELEVENLABS_CREATOR_CHARS:
            return self.ELEVENLABS_CREATOR_PRICE
        elif total_chars <= self.ELEVENLABS_PRO_CHARS:
            return self.ELEVENLABS_PRO_PRICE
        else:
            # Over Pro limit - would need Enterprise (assume Pro + overage)
            return self.ELEVENLABS_PRO_PRICE
    
    async def get_cost_recommendation(self) -> dict:
        """Get personalized cost recommendation based on last month's usage."""
        
        # Get last full month's usage
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
        
        result = await self.session.execute(
            select(PodcastUsageStats)
            .where(
                PodcastUsageStats.user_id == self.user.id,
                PodcastUsageStats.month == last_month
            )
        )
        stats = result.scalar_one_or_none()
        
        if not stats or stats.total_characters == 0:
            return {
                "recommendation": "Start with free Kokoro voices",
                "reason": "No usage data yet",
                "estimated_monthly_cost": 0.00,
                "suggested_provider": "kokoro"
            }
        
        # Calculate what each would have cost
        chars = stats.total_characters
        openai_cost = float(self._calculate_openai_cost(chars))
        elevenlabs_cost = float(self._calculate_elevenlabs_cost(chars))
        
        # Determine recommendation
        if chars <= 2000:  # 1 podcast
            return {
                "recommendation": "Stay with free Kokoro",
                "reason": f"Only {stats.podcast_count} podcast last month",
                "estimated_monthly_cost": 0.00,
                "suggested_provider": "kokoro"
            }
        
        elif openai_cost < elevenlabs_cost:
            savings = elevenlabs_cost - openai_cost
            return {
                "recommendation": "Use OpenAI TTS (pay-per-use)",
                "reason": f"{stats.podcast_count} podcasts/month = ${openai_cost:.2f} vs ${elevenlabs_cost:.2f} subscription",
                "estimated_monthly_cost": openai_cost,
                "suggested_provider": "openai",
                "savings": f"${savings:.2f}/month vs ElevenLabs"
            }
        
        else:
            savings = openai_cost - elevenlabs_cost
            return {
                "recommendation": "Subscribe to ElevenLabs Creator ($5/month)",
                "reason": f"{stats.podcast_count} podcasts/month = ${elevenlabs_cost:.2f} flat vs ${openai_cost:.2f} per-use",
                "estimated_monthly_cost": elevenlabs_cost,
                "suggested_provider": "elevenlabs",
                "savings": f"${savings:.2f}/month vs OpenAI"
            }
    
    async def track_usage(self, podcast: Podcast, provider: str, char_count: int):
        """Track podcast generation for cost analysis."""
        
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get or create stats for this month
        result = await self.session.execute(
            select(PodcastUsageStats)
            .where(
                PodcastUsageStats.user_id == self.user.id,
                PodcastUsageStats.month == current_month
            )
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = PodcastUsageStats(
                user_id=self.user.id,
                month=current_month
            )
            self.session.add(stats)
        
        # Update stats
        stats.podcast_count += 1
        stats.total_characters += char_count
        
        if provider == 'kokoro':
            stats.kokoro_count += 1
        elif provider == 'openai':
            stats.openai_count += 1
        elif provider == 'elevenlabs':
            stats.elevenlabs_count += 1
        
        # Calculate costs
        stats.estimated_openai_cost = self._calculate_openai_cost(stats.total_characters)
        stats.estimated_elevenlabs_cost = self._calculate_elevenlabs_cost(stats.total_characters)
        
        await self.session.commit()
```

---

## Usage in Podcast Generation

```python
# app/tasks/podcast_tasks.py

@shared_task
async def generate_podcast_task(podcast_id: int):
    """Background task with smart TTS selection."""
    
    async with get_async_session_context() as session:
        podcast = await session.get(Podcast, podcast_id)
        user = podcast.user
        
        # Initialize smart TTS service
        smart_tts = SmartTTSService(user, session)
        
        # Generate transcript
        transcript = await generate_transcript(...)
        
        # Estimate character count
        total_chars = sum(len(entry.dialog) for entry in transcript)
        
        # Get optimal provider
        provider = await smart_tts.get_optimal_provider(total_chars)
        
        print(f"Using {provider} TTS (optimal for this user's usage pattern)")
        
        # Generate audio with selected provider
        tts_service = TTSService(user, provider=provider)
        audio_segments = []
        
        for entry in transcript:
            audio = await tts_service.synthesize(entry.dialog, entry.speaker_id)
            audio_segments.append(audio)
        
        # Merge and save
        final_audio = await merge_audio_segments(audio_segments)
        
        # Track usage for future optimization
        await smart_tts.track_usage(podcast, provider, total_chars)
        
        # Save podcast
        podcast.file_location = await save_audio(final_audio)
        podcast.generation_status = "complete"
        await session.commit()
```

---

## User Dashboard: Cost Analytics

```typescript
// Dashboard component showing cost insights

interface CostAnalytics {
  last_month: {
    podcasts_generated: number;
    total_cost: number;
    provider_used: string;
    could_have_saved: number | null;
  };
  this_month: {
    podcasts_generated: number;
    projected_cost: number;
    recommended_provider: string;
  };
  recommendation: {
    title: string;
    description: string;
    action?: string;
  };
}

// Example output
{
  last_month: {
    podcasts_generated: 8,
    total_cost: 5.00,  // ElevenLabs Creator
    provider_used: "elevenlabs",
    could_have_saved: null  // This was optimal
  },
  this_month: {
    podcasts_generated: 3,
    projected_cost: 0.14,  // OpenAI would be cheaper
    recommended_provider: "openai"
  },
  recommendation: {
    title: "Save money this month",
    description: "You're on track for only 3 podcasts. OpenAI pay-per-use ($0.14) would be cheaper than your $5 ElevenLabs subscription.",
    action: "Switch to OpenAI for this month"
  }
}
```

---

## Settings UI: Smart Optimization

```
┌─────────────────────────────────────────────────────┐
│ Voice Provider Optimization                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Optimization Mode                                   │
│ ● Auto (Recommended)                                │
│   → Uses cheapest option based on usage             │
│                                                     │
│ ○ Prefer OpenAI TTS                                │
│   → Always use pay-per-use if key provided          │
│                                                     │
│ ○ Prefer ElevenLabs                                │
│   → Always use subscription if key provided         │
│                                                     │
│ ○ Free Only (Kokoro)                               │
│   → Never use paid services                         │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Last Month Analysis                                 │
│                                                     │
│ 12 podcasts generated                               │
│ Cost with OpenAI: $0.54                            │
│ Cost with ElevenLabs: $5.00                        │
│                                                     │
│ ✅ Auto mode used OpenAI - saved you $4.46         │
│                                                     │
├─────────────────────────────────────────────────────┤
│ This Month Projection                               │
│                                                     │
│ 4 podcasts so far                                   │
│ Projected: ~8 podcasts                              │
│                                                     │
│ 💡 Keep using OpenAI (~$0.36/month)                │
│    ElevenLabs would cost $5.00                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Key Benefits

### For Users
1. **No thinking required**: Just provide both keys, HERO optimizes
2. **Always cheapest**: System picks best option each month
3. **Transparent**: See exactly what you're paying and what you saved
4. **Flexible**: Override if you prefer specific provider

### For HERO
1. **Value-add feature**: "We optimize your AI costs"
2. **Encourages both keys**: Users want auto-optimization
3. **Data insights**: Understand usage patterns
4. **Marketing**: "Users save average of $X/month"

### For Revenue (Future)
1. **Premium tier**: "Advanced cost optimization" ($5/month)
2. **Bulk API keys**: HERO negotiates rates, passes savings
3. **Usage analytics**: Detailed cost breakdowns ($3/month add-on)

---

## Implementation Phases

### Phase 1: Basic (Now)
- Support both OpenAI and ElevenLabs
- Manual selection in settings
- Show cost estimates

### Phase 2: Smart Recommendations (Next)
- Track usage statistics
- Show monthly cost analysis
- Recommend optimal provider

### Phase 3: Auto-Optimization (Future)
- Enable "auto" mode
- Automatically choose cheapest each month
- Show savings dashboard

---

## Cost Comparison Examples

**Light user** (2 podcasts/month, ~6,000 chars):
- Kokoro: $0
- OpenAI: $0.09
- ElevenLabs: $5 (overkill)
- **Optimal**: Kokoro or OpenAI if quality matters

**Medium user** (10 podcasts/month, ~30,000 chars):
- Kokoro: $0
- OpenAI: $0.45
- ElevenLabs: $5
- **Optimal**: OpenAI (saves $4.55) or ElevenLabs if quality critical

**Power user** (40 podcasts/month, ~120,000 chars):
- Kokoro: $0
- OpenAI: $1.80
- ElevenLabs: $22
- **Optimal**: OpenAI (saves $20.20!)

**Heavy user** (100 podcasts/month, ~300,000 chars):
- OpenAI: $4.50
- ElevenLabs: $99 (Enterprise)
- **Optimal**: OpenAI (saves $94.50!)

---

## Database Migration

```sql
-- Add API keys
ALTER TABLE "user" ADD COLUMN openai_api_key VARCHAR(255);
ALTER TABLE "user" ADD COLUMN elevenlabs_api_key VARCHAR(255);
ALTER TABLE "user" ADD COLUMN tts_optimization_mode VARCHAR(50) DEFAULT 'auto';

-- Usage tracking table
CREATE TABLE podcast_usage_stats (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    month DATE NOT NULL,
    podcast_count INTEGER DEFAULT 0,
    total_characters INTEGER DEFAULT 0,
    kokoro_count INTEGER DEFAULT 0,
    openai_count INTEGER DEFAULT 0,
    elevenlabs_count INTEGER DEFAULT 0,
    estimated_openai_cost DECIMAL(10,4),
    estimated_elevenlabs_cost DECIMAL(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, month)
);

CREATE INDEX idx_usage_stats_user_month ON podcast_usage_stats(user_id, month);
```

---

**Created**: 2025-01-04  
**Status**: Design Complete  
**Next**: Implement Phase 1 (dual provider support)
