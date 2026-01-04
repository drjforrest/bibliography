# Clerk Environment Variables Verification

This document verifies that all Clerk environment variable names in the codebase match the official Clerk-provided variable names.

## Clerk Official Environment Variables

According to Clerk's official documentation, these are the standard environment variable names:

### Backend Variables
- **`CLERK_SECRET_KEY`** - The secret key for backend API calls (format: `sk_test_...` or `sk_live_...`)
- **`CLERK_PUBLISHABLE_KEY`** - The publishable key (format: `pk_test_...` or `pk_live_...`)
- **`CLERK_WEBHOOK_SECRET`** - The webhook signing secret for verifying webhook requests

### Frontend Variables (Next.js)
- **`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`** - The publishable key for frontend (must be prefixed with `NEXT_PUBLIC_` for Next.js)
- **`NEXT_PUBLIC_CLERK_SIGN_IN_URL`** - Optional: Custom sign-in URL
- **`NEXT_PUBLIC_CLERK_SIGN_UP_URL`** - Optional: Custom sign-up URL

### Custom Configuration Variables
These are not provided by Clerk but are required for JWT verification:
- **`CLERK_ISSUER`** - The JWT issuer URL (e.g., `https://clerk.counterforce-hero.tech`)
- **`CLERK_JWKS_URL`** - The JWKS endpoint URL (e.g., `https://clerk.counterforce-hero.tech/.well-known/jwks.json`)
- **`CLERK_AUDIENCE`** - Optional: JWT audience for token verification

## Code Verification

### Backend Configuration (`backend/app/config/__init__.py`)

| Line | Code | Env Variable Read | Clerk Official Name | Status |
|------|------|-------------------|---------------------|--------|
| 152 | `CLERK_API_KEY = os.getenv("CLERK_SECRET_KEY")` | `CLERK_SECRET_KEY` | `CLERK_SECRET_KEY` | ✅ **CORRECT** |
| 153 | `CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")` | `CLERK_PUBLISHABLE_KEY` | `CLERK_PUBLISHABLE_KEY` | ✅ **CORRECT** |
| 154 | `CLERK_WEBHOOK_SIGNING_KEY = os.getenv("CLERK_WEBHOOK_SECRET")` | `CLERK_WEBHOOK_SECRET` | `CLERK_WEBHOOK_SECRET` | ✅ **CORRECT** |
| 171 | `CLERK_ISSUER = os.getenv("CLERK_ISSUER", ...)` | `CLERK_ISSUER` | Custom (not from Clerk) | ✅ **CORRECT** |
| 178 | `CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", ...)` | `CLERK_JWKS_URL` | Custom (not from Clerk) | ✅ **CORRECT** |
| 186 | `CLERK_AUDIENCE = os.getenv("CLERK_AUDIENCE")` | `CLERK_AUDIENCE` | Custom (optional) | ✅ **CORRECT** |

**Note**: The internal variable name `CLERK_API_KEY` is fine - it's just an internal name. The important thing is that it reads `CLERK_SECRET_KEY` from the environment, which matches Clerk's official name.

### Frontend Configuration

#### `frontend/nextjs-app/app/layout.tsx`
- **ClerkProvider** automatically reads `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` from environment
- ✅ **CORRECT** - This matches Clerk's official Next.js variable name

#### `frontend/nextjs-app/middleware.ts`
- Line 17: `process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL` - Optional, has default
- ✅ **CORRECT** - This is a custom variable for redirect URL

#### `frontend/nextjs-app/app/auth/login/page.tsx`
- Line 8: `process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL` - Optional, has default
- ✅ **CORRECT** - This is a custom variable for redirect URL

#### `frontend/nextjs-app/app/auth/register/page.tsx`
- Line 8: `process.env.NEXT_PUBLIC_CLERK_SIGN_UP_URL` - Optional, has default
- ✅ **CORRECT** - This is a custom variable for redirect URL

## Required Environment Variables

### Backend `.env` or `.env.production`

```bash
# Required Clerk Variables (from Clerk Dashboard)
CLERK_SECRET_KEY=sk_live_...          # Secret key from Clerk Dashboard
CLERK_PUBLISHABLE_KEY=pk_live_...     # Publishable key from Clerk Dashboard
CLERK_WEBHOOK_SECRET=whsec_...        # Webhook secret from Clerk Dashboard

# Required Custom Variables (for JWT verification)
CLERK_ISSUER=https://clerk.counterforce-hero.tech
CLERK_JWKS_URL=https://clerk.counterforce-hero.tech/.well-known/jwks.json

# Optional
CLERK_AUDIENCE=                        # Optional: JWT audience
APP_ENV=production                     # Set to "production" to use default issuer/JWKS URLs
```

### Frontend `.env.local` or `.env.production`

```bash
# Required Clerk Variable (from Clerk Dashboard)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...  # Must match backend CLERK_PUBLISHABLE_KEY

# Optional Custom Variables
NEXT_PUBLIC_CLERK_SIGN_IN_URL=https://accounts.counterforce-hero.tech/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=https://accounts.counterforce-hero.tech/sign-up
NEXT_PUBLIC_API_URL=http://localhost:8000        # Backend API URL
```

## Common Mistakes to Avoid

### ❌ WRONG Variable Names
```bash
# DON'T USE THESE:
CLERK_API_KEY=...              # Wrong - should be CLERK_SECRET_KEY
CLERK_SECRET=...               # Wrong - should be CLERK_SECRET_KEY
CLERK_WEBHOOK_KEY=...          # Wrong - should be CLERK_WEBHOOK_SECRET
CLERK_PUBLIC_KEY=...           # Wrong - should be CLERK_PUBLISHABLE_KEY
```

### ✅ CORRECT Variable Names
```bash
# USE THESE:
CLERK_SECRET_KEY=...           # ✅ Correct
CLERK_PUBLISHABLE_KEY=...      # ✅ Correct
CLERK_WEBHOOK_SECRET=...       # ✅ Correct
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...  # ✅ Correct for Next.js
```

## Verification Checklist

- [ ] `CLERK_SECRET_KEY` is set in backend `.env` (not `CLERK_API_KEY`)
- [ ] `CLERK_PUBLISHABLE_KEY` is set in backend `.env`
- [ ] `CLERK_WEBHOOK_SECRET` is set in backend `.env` (not `CLERK_WEBHOOK_KEY`)
- [ ] `CLERK_ISSUER` is set in backend `.env` (or `APP_ENV=production` for defaults)
- [ ] `CLERK_JWKS_URL` is set in backend `.env` (or `APP_ENV=production` for defaults)
- [ ] `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is set in frontend `.env.local` (must match backend value)
- [ ] All keys are from the same Clerk instance (test vs live)
- [ ] Keys match the environment (test keys for dev, live keys for production)

## Clerk Export Format Compatibility

**Updated**: The code now supports both explicit variable names and Clerk's export format:

### Variable Mappings (Fallback Support)

| Code Expects | Clerk Provides | Status |
|-------------|----------------|--------|
| `CLERK_SECRET_KEY` | `CLERK_SECRET_KEY` | ✅ Direct match |
| `CLERK_PUBLISHABLE_KEY` | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | ✅ **Now supported** - code uses NEXT_PUBLIC version as fallback |
| `CLERK_ISSUER` | `CLERK_FRONTEND_API_URL` | ✅ **Now supported** - code uses CLERK_FRONTEND_API_URL as fallback |
| `CLERK_JWKS_URL` | `CLERK_JWKS_URL` | ✅ Direct match |
| `CLERK_WEBHOOK_SECRET` | (Not in export - from webhook settings) | ⚠️ Must be set separately |

### Clerk Export Format

When you copy/paste from Clerk Dashboard, you get:
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
CLERK_FRONTEND_API_URL=https://clerk.counterforce-hero.tech
CLERK_JWKS_URL=https://clerk.counterforce-hero.tech/.well-known/jwks.json
```

The code now automatically uses:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` if `CLERK_PUBLISHABLE_KEY` is not set
- `CLERK_FRONTEND_API_URL` if `CLERK_ISSUER` is not set

## Summary

✅ **Code updated to support Clerk's export format directly!**

The code now correctly reads:
- `CLERK_SECRET_KEY` ✅
- `CLERK_PUBLISHABLE_KEY` or `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (fallback) ✅
- `CLERK_ISSUER` or `CLERK_FRONTEND_API_URL` (fallback) ✅
- `CLERK_JWKS_URL` ✅
- `CLERK_WEBHOOK_SECRET` (must be set from webhook settings) ⚠️

**Note**: `CLERK_WEBHOOK_SECRET` is not included in Clerk's export. You must add it separately from your Clerk Dashboard → Webhooks → Signing Secret.

