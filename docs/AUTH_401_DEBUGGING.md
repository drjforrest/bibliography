# Authentication 401 Error Debugging Guide

## Issue
API calls to `api.counterforce-hero.tech` are returning 401 (Unauthorized) errors, even though tokens are being sent from the frontend.

## Symptoms
- ✅ Frontend is sending tokens (console shows "✅ Token attached to request")
- ✅ Requests are going to correct domain (`api.counterforce-hero.tech`)
- ❌ Backend returns 401 Unauthorized
- ❌ Console shows "Authentication error"

## Debugging Steps

### 1. Check Backend Environment Variables

Verify these are set on the production backend (mac-mini):

```bash
# SSH to mac-mini
ssh mac-mini
cd ~/production/hero-evidence-library/backend

# Check environment variables
grep -E "CLERK_|APP_ENV" .env || echo "No .env file found or no Clerk vars"

# Should have:
# CLERK_SECRET_KEY=sk_live_...
# CLERK_PUBLISHABLE_KEY=pk_live_...
# CLERK_ISSUER=https://clerk.counterforce-hero.tech
# CLERK_JWKS_URL=https://clerk.counterforce-hero.tech/.well-known/jwks.json
# CLERK_WEBHOOK_SECRET=whsec_...
```

### 2. Check Backend Logs

```bash
# On mac-mini, check backend logs
tail -50 ~/production/hero-evidence-library/hero_evidence_library_backend.log

# Look for:
# - "Authentication required but no credentials provided"
# - "Error authenticating with Clerk"
# - "Failed to fetch JWKS"
# - "Token missing key ID (kid)"
# - "Key not found in JWKS"
# - "Invalid token claims"
```

### 3. Test JWKS Endpoint

Verify the JWKS endpoint is accessible from the backend:

```bash
# From mac-mini
curl -s https://clerk.counterforce-hero.tech/.well-known/jwks.json | head -20
# Should return JSON with "keys" array
```

### 4. Test Token Format (Frontend)

In browser console, check what token is being sent:

```javascript
// In browser console on library.counterforce-hero.tech
const { getToken } = useAuth();
const token = await getToken();
console.log('Token preview:', token?.substring(0, 50) + '...');
console.log('Token length:', token?.length);
```

### 5. Verify Clerk JWT Template

The Clerk JWT template must include:
- `sub` (user ID) - REQUIRED
- `email` - REQUIRED for user creation
- `iss` should match `CLERK_ISSUER`
- `aud` (if CLERK_AUDIENCE is set)

Check Clerk Dashboard → JWT Templates → Your Template

## Common Issues

### Issue 1: Missing CLERK_ISSUER or CLERK_JWKS_URL

**Symptom**: Backend fails to start or errors on token verification

**Fix**: Set in backend `.env`:
```bash
CLERK_ISSUER=https://clerk.counterforce-hero.tech
CLERK_JWKS_URL=https://clerk.counterforce-hero.tech/.well-known/jwks.json
```

### Issue 2: JWKS Endpoint Not Accessible

**Symptom**: "Failed to fetch JWKS" errors in logs

**Fix**: 
- Verify `clerk.counterforce-hero.tech` DNS is correct
- Verify Clerk instance is accessible
- Check firewall/network connectivity from backend

### Issue 3: Token Issuer Mismatch

**Symptom**: Token verification fails with issuer mismatch

**Fix**: Ensure `CLERK_ISSUER` matches the issuer in the JWT token. Check token claims:
```python
# In backend, unverified payload shows:
# "iss": "https://clerk.counterforce-hero.tech"
# CLERK_ISSUER must match exactly
```

### Issue 4: Token Missing Required Claims

**Symptom**: "Invalid token claims: missing sub" or "Email not in token"

**Fix**: 
- Update Clerk JWT Template to include `sub` and `email`
- Ensure JWT template is set for the correct environment (production)

### Issue 5: Token Format Issues

**Symptom**: "Token missing key ID (kid)" or "Key not found in JWKS"

**Fix**:
- Token should be a valid JWT with proper header
- Verify Clerk is generating tokens correctly
- Check if token is being truncated or modified

## Quick Test Endpoint

You can test token verification manually:

```bash
# Get token from browser console (see step 4 above)
TOKEN="your_token_here"

# Test against backend
curl -X GET "https://api.counterforce-hero.tech/api/v1/papers?limit=1" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

## Next Steps

1. **Check backend logs** first - this will show the exact error
2. **Verify environment variables** are set correctly
3. **Test JWKS endpoint** accessibility
4. **Check Clerk JWT template** configuration
5. **Verify token format** in browser console

After identifying the specific error from logs, we can apply the appropriate fix.

