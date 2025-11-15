# OpenRouter Migration Guide

## Summary

The user profile system has been updated to use **OpenRouter** instead of separate OpenAI and Anthropic API keys. This provides users with access to 100+ AI models through a single API key.

## What Changed

### Before
- Users had separate fields for OpenAI and Anthropic API keys
- Limited to 2 AI providers
- More complex API key management

### After
- Single OpenRouter API key field
- Access to 100+ models from multiple providers
- Simplified API key management
- Better model selection and pricing transparency

## Key Benefits

### 1. **Unified Access**
One API key provides access to:
- GPT-4, GPT-4 Turbo, GPT-3.5 (OpenAI)
- Claude 3 Opus, Sonnet, Haiku (Anthropic)
- Gemini Pro, Gemini Ultra (Google)
- Llama 3, Llama 2 (Meta)
- Mixtral, Mistral Large (Mistral)
- Many open-source models

### 2. **Cost Transparency**
- Clear pricing for each model
- Pay-as-you-go with no subscriptions
- Usage tracking and monitoring

### 3. **Flexibility**
- Switch between models easily
- Try new models as they become available
- No need to manage multiple API keys

## System Architecture

### RAG System (System-Level)
- **Location**: `.env` file
- **Uses**: LiteLLM with configured models
- **Purpose**: Document-based RAG features
- **Managed by**: System administrators

### User Chat (User-Level)
- **Location**: User profile (`openrouter_api_key`)
- **Uses**: OpenRouter API
- **Purpose**: General chat features with model selection
- **Managed by**: Individual users

## Migration Steps

### 1. Run Database Migration

```bash
cd backend
python scripts/add_user_profile_fields.py
```

This will:
- Add `openrouter_api_key` column
- Remove `openai_api_key` column (if exists)
- Remove `anthropic_api_key` column (if exists)
- Add profile fields (`display_name`, `bio`, `avatar_url`)

### 2. Update Environment

No changes needed to `.env` - RAG system continues to use existing LiteLLM configuration.

### 3. Inform Users

Users will need to:
1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Get their API key
3. Add it to their profile at `/profile`

## For Developers

### Database Schema

```sql
-- New field
openrouter_api_key VARCHAR

-- Removed fields (migration handles this)
-- openai_api_key
-- anthropic_api_key
```

### API Changes

#### Endpoints
```
GET  /api/v1/profile          # Now includes openrouter_api_key_set
PUT  /api/v1/profile          # Profile updates
GET  /api/v1/api-keys         # Returns openrouter_api_key_set
PUT  /api/v1/api-keys         # Updates openrouter_api_key
```

#### Response Format

**Before:**
```json
{
  "openai_api_key_set": true,
  "anthropic_api_key_set": false
}
```

**After:**
```json
{
  "openrouter_api_key_set": true
}
```

### Using OpenRouter in Code

When implementing chat features that use the user's OpenRouter key:

```python
from langchain_litellm import ChatLiteLLM

# Get user's OpenRouter key from database
openrouter_key = user.openrouter_api_key

# Initialize LiteLLM with OpenRouter
llm = ChatLiteLLM(
    model="openrouter/anthropic/claude-3-sonnet",  # Example model
    api_key=openrouter_key,
    api_base="https://openrouter.ai/api/v1"
)

# Use the LLM
response = llm.invoke("Your prompt here")
```

## OpenRouter Model Format

Models on OpenRouter use the format: `openrouter/{provider}/{model}`

Examples:
- `openrouter/openai/gpt-4`
- `openrouter/anthropic/claude-3-opus`
- `openrouter/google/gemini-pro`
- `openrouter/meta-llama/llama-3-70b`

## Pricing

OpenRouter uses transparent, pay-as-you-go pricing:
- No monthly subscriptions
- Pay only for what you use
- Prices vary by model
- View pricing at: https://openrouter.ai/models

## Backward Compatibility

The migration script safely handles:
- Existing users with old API keys
- Fresh installations without old fields
- Idempotent operation (safe to run multiple times)

Old API keys are removed during migration, so users will need to set up OpenRouter keys.

## Support & Documentation

- **OpenRouter Docs**: https://openrouter.ai/docs
- **Model List**: https://openrouter.ai/models
- **Pricing**: https://openrouter.ai/models (includes pricing)
- **API Status**: https://status.openrouter.ai

## FAQ

### Q: What happens to existing OpenAI/Anthropic keys?
A: They are removed during migration. Users need to create OpenRouter accounts.

### Q: Does the RAG system change?
A: No, RAG continues to use system-level LiteLLM configuration from `.env`.

### Q: Can users still use GPT-4 and Claude?
A: Yes! All models are available through OpenRouter.

### Q: Is OpenRouter more expensive?
A: Pricing is competitive and transparent. Many models are cheaper than direct API access.

### Q: Do I need to change my .env file?
A: No, system-level RAG configuration remains unchanged.

### Q: What if a user doesn't set an OpenRouter key?
A: Chat features requiring user keys won't work until they set one. RAG features using system keys work normally.

## Rollout Checklist

- [x] Update database schema
- [x] Update backend API endpoints
- [x] Update frontend profile page
- [x] Update migration script
- [x] Update documentation
- [ ] Run migration on production database
- [ ] Test profile page
- [ ] Test API key storage and retrieval
- [ ] Notify users about the change
- [ ] Update user onboarding materials

## Next Steps

1. **Test the migration** on a development database first
2. **Backup production** database before running migration
3. **Run migration** during low-traffic period
4. **Monitor logs** for any errors
5. **Communicate** with users about the change and how to get OpenRouter keys

## Example User Communication

```
Subject: New Feature: Access 100+ AI Models with OpenRouter

We've upgraded the AI capabilities in [Your App Name]!

What's New:
- Single API key for 100+ AI models
- Access to GPT-4, Claude 3, Gemini Pro, and more
- Better pricing and model selection

Action Required:
1. Visit your profile page
2. Sign up at openrouter.ai (free)
3. Add your OpenRouter API key

Get started: [Link to profile page]
Learn more: [Link to documentation]
```
