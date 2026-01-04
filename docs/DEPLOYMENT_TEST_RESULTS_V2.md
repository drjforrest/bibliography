# Deployment Test Results - Round 2

**Date**: 2025-01-03  
**Tested By**: MCP Browser Tools  
**Environment**: Production (https://library.counterforce-hero.tech)  
**After**: Redeployment

## Test Summary

After redeployment, the same CSP violation issue persists. The frontend is still not using the correct API URL.

## Current Status

### ✅ Still Working
- Frontend loads at https://library.counterforce-hero.tech
- Backend API accessible at https://api.counterforce-hero.tech
- Health endpoint: ✅ 200 OK
- UI renders correctly
- Clerk authentication functional

### ❌ Issue Persists

**Problem**: Frontend is still trying to use localhost (CSP violation) or using relative paths instead of the API domain.

**Console Error** (still present):
```
Refused to connect to 'https://localhost:8400/api/v1/papers/?limit=100' 
because it violates the following Content Security Policy directive
```

**Network Requests Observed**:
- Requests going to: `https://library.counterforce-hero.tech/api/v1/papers`
- Should be going to: `https://api.counterforce-hero.tech/api/v1/papers`

This indicates `NEXT_PUBLIC_API_URL` is either:
1. Not set in `.env.local` before build
2. Set but not being picked up by Next.js build
3. The build is using cached/stale environment variables

## Root Cause Analysis

**Next.js Environment Variable Behavior**:
- `NEXT_PUBLIC_*` variables are embedded at **build time**, not runtime
- They must be present in `.env.local` (or `.env.production.local`) **before** running `npm run build`
- If not set, the code uses fallback values (empty string = relative paths)
- After build, changing `.env.local` does NOT update the embedded values

**Current Behavior**:
The code is using relative paths (`/api/v1/papers`) which go through Next.js rewrites to `http://localhost:8400`, but somehow the browser is seeing `https://localhost:8400` in the CSP error.

## Required Fix

The deployment script (`deploy.sh`) does set `NEXT_PUBLIC_API_URL` in `.env.local` before building (line 250), but one of these might be happening:

1. **The `.env.local` file already exists** from a previous build, and the script doesn't overwrite it (line 255: "Using existing .env.local")
2. **Build cache** - Next.js might be using cached build output
3. **Build didn't run** - The frontend might not have been rebuilt

### Verification Steps

1. **Check if `.env.local` exists and has correct value**:
   ```bash
   ssh mac-mini
   cd ~/production/hero-evidence-library/frontend/nextjs-app
   cat .env.local | grep NEXT_PUBLIC_API_URL
   # Should show: NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech
   ```

2. **Check build timestamp**:
   ```bash
   ls -la .next/
   # Check if build is recent
   ```

3. **Force clean rebuild**:
   ```bash
   rm -rf .next
   # Ensure .env.local has NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech
   npm run build
   ```

4. **Verify in browser**:
   - Open browser DevTools → Network tab
   - Refresh page
   - Check API requests - they should go to `api.counterforce-hero.tech`, not `library.counterforce-hero.tech/api`

## Recommendations

1. **Modify deploy.sh** to force update `.env.local`:
   ```bash
   # Always ensure NEXT_PUBLIC_API_URL is set correctly
   if ! grep -q "NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech" .env.local 2>/dev/null; then
     echo "NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech" >> .env.local
   fi
   ```

2. **Add clean build step**:
   ```bash
   rm -rf .next
   npm run build
   ```

3. **Verify build output** (check that API URL is embedded):
   ```bash
   grep -r "api.counterforce-hero.tech" .next/static/chunks/*.js | head -5
   # Should find references to the API domain
   ```

---

**Status**: Issue persists - needs manual verification and potential rebuild on production server.

