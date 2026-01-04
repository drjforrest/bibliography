# OpenRouter Model Options for HERO Evidence Library

## Overview

Users can set their preferred LLM model in `default_openrouter_model` field. This model will be used for:
- Podcast transcript generation
- Paper summaries (all types)
- Any LLM-powered features

## Recommended Models for Podcast Generation

### Best Balance: Quality + Cost

**1. Anthropic Claude Sonnet 4 (Default)**
```
Model ID: anthropic/claude-sonnet-4-20250514
Pricing: $3/M input, $15/M output
Context: 200k tokens
Speed: Fast
Quality: ★★★★★

Best for: High-quality podcasts with nuanced discussion
Est. cost per podcast: ~$0.135
```

**2. OpenAI GPT-4o Mini**
```
Model ID: openai/gpt-4o-mini
Pricing: $0.15/M input, $0.60/M output
Context: 128k tokens
Speed: Very fast
Quality: ★★★★☆

Best for: Budget-conscious users, quick generation
Est. cost per podcast: ~$0.006 (23x cheaper than Claude!)
```

### Premium Quality

**3. OpenAI GPT-4o**
```
Model ID: openai/gpt-4o
Pricing: $2.50/M input, $10/M output
Context: 128k tokens
Speed: Fast
Quality: ★★★★★

Best for: Professional podcasts, complex papers
Est. cost per podcast: ~$0.10
```

**4. Anthropic Claude Opus 4.1**
```
Model ID: anthropic/claude-opus-4.1-20250514
Pricing: $15/M input, $75/M output
Context: 200k tokens
Speed: Medium
Quality: ★★★★★★

Best for: Maximum quality, complex synthesis
Est. cost per podcast: ~$0.60 (most expensive)
```

### Budget Options

**5. Google Gemini 2.0 Flash**
```
Model ID: google/gemini-2.0-flash-exp:free
Pricing: FREE (rate limited)
Context: 1M tokens
Speed: Very fast
Quality: ★★★★☆

Best for: Free tier users, experimentation
Est. cost per podcast: $0
Note: Rate limits apply
```

**6. Meta Llama 3.3 70B**
```
Model ID: meta-llama/llama-3.3-70b-instruct
Pricing: $0.35/M input, $0.40/M output
Context: 128k tokens
Speed: Fast
Quality: ★★★★☆

Best for: Budget + quality balance
Est. cost per podcast: ~$0.015
```

### Specialized Options

**7. Mistral Large**
```
Model ID: mistralai/mistral-large
Pricing: $2/M input, $6/M output
Context: 128k tokens
Speed: Fast
Quality: ★★★★☆

Best for: European users, multi-language support
Est. cost per podcast: ~$0.08
```

**8. Perplexity Sonar**
```
Model ID: perplexity/sonar-pro
Pricing: $3/M input, $15/M output
Context: 200k tokens
Speed: Fast
Quality: ★★★★★
Special: Web-enhanced responses

Best for: Current events, real-time data needs
Est. cost per podcast: ~$0.135
```

---

## Model Selection Guidance

### For Academic Research Podcasts

**Recommended**: Claude Sonnet 4 or GPT-4o
- Excellent reasoning and synthesis
- Handles complex papers well
- Natural dialogue generation
- Good value for quality

### For High-Volume Users

**Recommended**: GPT-4o Mini or Gemini Flash
- Lowest costs
- Fast generation
- Good enough quality
- Scale to 100+ podcasts/month affordably

### For Maximum Quality

**Recommended**: Claude Opus 4.1
- Best reasoning capabilities
- Most nuanced discussions
- Worth the cost for flagship content

### For Budget Constraints

**Recommended**: Gemini Flash (free tier) or Llama 3.3
- Zero or minimal cost
- Acceptable quality
- Good for experimentation

---

## Cost Estimates (Per Podcast)

Assumes:
- 20k input tokens (paper context)
- 5k output tokens (podcast transcript)

| Model | Input Cost | Output Cost | Total/Podcast |
|-------|-----------|-------------|---------------|
| **GPT-4o Mini** | $0.003 | $0.003 | **$0.006** ⭐ Best value |
| Llama 3.3 70B | $0.007 | $0.002 | $0.009 |
| Gemini Flash | $0.00 | $0.00 | **$0.00** 🆓 Free |
| Mistral Large | $0.04 | $0.03 | $0.07 |
| GPT-4o | $0.05 | $0.05 | $0.10 |
| Claude Sonnet 4 | $0.06 | $0.075 | **$0.135** ⭐ Default |
| Perplexity Sonar | $0.06 | $0.075 | $0.135 |
| **Claude Opus 4.1** | $0.30 | $0.375 | **$0.675** 💎 Premium |

---

## Settings UI - Model Selector

```typescript
interface ModelOption {
  id: string;
  name: string;
  provider: string;
  pricing: string;
  quality: number; // 1-5 stars
  speed: string;
  recommended?: string;
}

const popularModels: ModelOption[] = [
  {
    id: 'anthropic/claude-sonnet-4-20250514',
    name: 'Claude Sonnet 4',
    provider: 'Anthropic',
    pricing: '$0.135/podcast',
    quality: 5,
    speed: 'Fast',
    recommended: 'Default - Best balance'
  },
  {
    id: 'openai/gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'OpenAI',
    pricing: '$0.006/podcast',
    quality: 4,
    speed: 'Very Fast',
    recommended: 'Best value'
  },
  {
    id: 'openai/gpt-4o',
    name: 'GPT-4o',
    provider: 'OpenAI',
    pricing: '$0.10/podcast',
    quality: 5,
    speed: 'Fast'
  },
  {
    id: 'anthropic/claude-opus-4.1-20250514',
    name: 'Claude Opus 4.1',
    provider: 'Anthropic',
    pricing: '$0.675/podcast',
    quality: 6,
    speed: 'Medium',
    recommended: 'Premium quality'
  },
  {
    id: 'google/gemini-2.0-flash-exp:free',
    name: 'Gemini 2.0 Flash',
    provider: 'Google',
    pricing: 'FREE',
    quality: 4,
    speed: 'Very Fast',
    recommended: 'Free tier'
  },
  {
    id: 'meta-llama/llama-3.3-70b-instruct',
    name: 'Llama 3.3 70B',
    provider: 'Meta',
    pricing: '$0.015/podcast',
    quality: 4,
    speed: 'Fast'
  }
];
```

## UI Component Example

```
┌─────────────────────────────────────────────────────────┐
│ LLM Model Selection                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Default Model for Podcast Generation                    │
│                                                         │
│ [Claude Sonnet 4 ▼]                                    │
│                                                         │
│ ℹ️  Selected: Claude Sonnet 4                          │
│    Quality: ★★★★★                                      │
│    Speed: Fast                                          │
│    Cost: ~$0.135 per podcast                           │
│                                                         │
│ Popular alternatives:                                   │
│                                                         │
│ • GPT-4o Mini - $0.006/podcast (23x cheaper!)          │
│ • GPT-4o - $0.10/podcast                               │
│ • Gemini Flash - FREE (rate limited)                   │
│                                                         │
│ [Advanced: Browse all 100+ models →]                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation in Services

### Using Default Model

```python
# app/services/podcast_llm_service.py

async def get_podcast_llm(
    user: User, 
    model_override: str = None
) -> BaseChatModel:
    """
    Get LLM for podcast generation.
    Uses user's default model if no override provided.
    """
    if not user.openrouter_api_key:
        raise ValueError("OpenRouter API key required")
    
    # Use override if provided, otherwise user's default, otherwise system default
    model = (
        model_override 
        or user.default_openrouter_model 
        or "anthropic/claude-sonnet-4-20250514"
    )
    
    return ChatOpenAI(
        model=model,
        api_key=user.decrypted_openrouter_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.7,
        max_tokens=8000
    )
```

### API Endpoint with Override

```python
# app/routes/podcast_routes.py

@router.post("/generate")
async def generate_podcast(
    request: GeneratePodcastRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate podcast with optional model override.
    
    Uses user's default_openrouter_model if model not specified.
    """
    llm = await get_podcast_llm(
        current_user, 
        model_override=request.model  # Optional field
    )
    
    # ... rest of generation logic
```

---

## Model Update Strategy

### When OpenRouter Adds New Models

1. **Don't break existing users**: Keep their `default_openrouter_model` working
2. **Add new options to UI**: Update frontend model list
3. **Notify power users**: "New models available!"
4. **Test compatibility**: Ensure new models work with podcast prompts

### Model Deprecation Handling

```python
# app/services/model_validation.py

DEPRECATED_MODELS = {
    'anthropic/claude-2': 'anthropic/claude-sonnet-4-20250514',
    'openai/gpt-4-32k': 'openai/gpt-4o'
}

async def validate_and_migrate_model(user: User) -> str:
    """
    Check if user's default model is deprecated.
    Automatically migrate to recommended replacement.
    """
    current_model = user.default_openrouter_model
    
    if current_model in DEPRECATED_MODELS:
        new_model = DEPRECATED_MODELS[current_model]
        
        # Update user's default
        user.default_openrouter_model = new_model
        await session.commit()
        
        # Notify user
        await create_notification(
            user_id=user.id,
            title="Model Updated",
            message=f"Your default model {current_model} was deprecated. Upgraded to {new_model}."
        )
        
        return new_model
    
    return current_model
```

---

## Advanced: Model Routing by Use Case

```python
# app/services/smart_model_router.py

class SmartModelRouter:
    """Route to optimal model based on task characteristics."""
    
    TASK_MODELS = {
        'quick_summary': 'openai/gpt-4o-mini',  # Fast, cheap
        'deep_analysis': 'anthropic/claude-sonnet-4-20250514',  # Quality
        'max_quality': 'anthropic/claude-opus-4.1-20250514',  # Premium
        'free_tier': 'google/gemini-2.0-flash-exp:free'  # Free
    }
    
    async def route_model(
        self,
        user: User,
        task_type: str,
        paper_count: int
    ) -> str:
        """
        Intelligently route to model based on:
        - Task complexity
        - User's budget preferences
        - Paper count
        """
        # Check user's preference first
        if user.default_openrouter_model:
            return user.default_openrouter_model
        
        # Route based on task
        if paper_count > 5:
            # Complex synthesis - use premium model
            return self.TASK_MODELS['deep_analysis']
        
        elif task_type == 'quick_podcast':
            # Quick turnaround - use fast/cheap model
            return self.TASK_MODELS['quick_summary']
        
        else:
            # Default balanced choice
            return self.TASK_MODELS['deep_analysis']
```

---

**Created**: 2025-01-04  
**Status**: Ready for implementation  
**Default Model**: Claude Sonnet 4 (`anthropic/claude-sonnet-4-20250514`)
