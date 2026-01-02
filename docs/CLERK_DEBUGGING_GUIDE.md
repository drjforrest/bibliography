# Clerk Authentication Debugging Guide

This guide helps diagnose and fix 403 Forbidden errors when using Clerk authentication with the backend API.

## Quick Debugging Steps

### Step 1: Test Token Verification

Use the debug endpoint to inspect your token:

```bash
# From your frontend or using curl
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:8000/debug/token
```

This endpoint returns:

- Whether a token is present
- Token claims (iss, aud, sub, email, exp, etc.)
- Configuration values (issuer, JWKS URL, audience)
- Verification status and any errors

### Step 2: Check Server Logs

The enhanced logging now provides detailed information:

```bash
# Check backend logs
tail -f logs/backend.log | grep -i clerk
```

Look for:

- Token verification attempts
- Issuer/audience mismatches
- Key ID (kid) lookups
- User authentication status

### Step 3: Verify Frontend Token Sending

In your browser console, check if tokens are being sent:

```javascript
// In your frontend code, add this temporarily:
const token = await getToken();
console.log("Token (first 50 chars):", token?.substring(0, 50));
console.log("Token present:", !!token);
```

Then check the Network tab:

1. Open DevTools → Network
2. Find a failing API request (e.g., `/api/v1/dashboard/user`)
3. Check the Request Headers for `Authorization: Bearer <token>`
4. If missing, the frontend isn't sending the token

## Common Issues and Solutions

### Issue 1: Token Not Being Sent

**Symptoms:**

- 401 Unauthorized errors
- Debug endpoint shows `"token_present": false`

**Solution:**

- Verify `createAuthenticatedClient` is being used in frontend
- Check that `getToken()` is called correctly
- Ensure the interceptor is adding the Authorization header

### Issue 2: Issuer Mismatch

**Symptoms:**

- 401 errors with "Invalid token issuer"
- Debug endpoint shows `"issuer_match": false`

**Solution:**

1. Check your `.env` file:
   ```bash
   CLERK_ISSUER=https://clerk.counterforce-hero.tech
   ```
2. Verify the token's issuer matches:
   - From Clerk Dashboard → API Keys
   - Should match your Clerk instance URL

### Issue 3: Audience Mismatch

**Symptoms:**

- 401 errors with "Invalid token audience"
- Token has different `aud` claim than expected

**Solution:**

1. If you need audience verification, set in `.env`:
   ```bash
   CLERK_AUDIENCE=your-api-audience
   ```
2. Most Clerk tokens don't require audience verification
3. Leave `CLERK_AUDIENCE` unset if not needed

### Issue 4: User Account Inactive

**Symptoms:**

- 403 Forbidden with "User account is inactive"
- Token verification succeeds but user is deactivated

**Solution:**

- Check database: `SELECT * FROM users WHERE clerk_user_id = '...'`
- Ensure `is_active = true` for the user
- User may have been soft-deleted via webhook

### Issue 5: Key ID (kid) Not Found

**Symptoms:**

- 401 errors with "Key not found in JWKS"
- JWKS endpoint returns different keys

**Solution:**

1. Verify JWKS URL is correct:
   ```bash
   CLERK_JWKS_URL=https://clerk.counterforce-hero.tech/.well-known/jwks.json
   ```
2. Check if JWKS is accessible:
   ```bash
   curl https://clerk.counterforce-hero.tech/.well-known/jwks.json
   ```
3. JWKS cache may be stale - restart backend to refresh

## Enhanced Logging Details

The following information is now logged at DEBUG level:

### Token Verification

- Token header and key ID (kid)
- JWKS fetch status and key count
- Token claims (iss, aud, sub, exp)
- Issuer/audience matching results
- Verification success/failure

### User Authentication

- User ID and email from token
- Database lookup results
- User active status
- Authentication success/failure

### Error Details

- Specific JWT validation errors
- HTTP exception details
- Full stack traces for unexpected errors

## Environment Configuration

Ensure these are set in your `.env`:

```bash
# Required
CLERK_SECRET_KEY=sk_test_... or sk_live_...
CLERK_PUBLISHABLE_KEY=pk_test_... or pk_live_...
CLERK_ISSUER=https://clerk.counterforce-hero.tech
CLERK_JWKS_URL=https://clerk.counterforce-hero.tech/.well-known/jwks.json

# Optional
CLERK_AUDIENCE=your-api-audience  # Only if you need audience verification
CLERK_WEBHOOK_SECRET=whsec_...     # For webhook verification
```

## Testing Checklist

- [ ] Token is present in Authorization header
- [ ] Token issuer matches `CLERK_ISSUER`
- [ ] Token audience matches `CLERK_AUDIENCE` (if set)
- [ ] Token is not expired
- [ ] JWKS endpoint is accessible
- [ ] Key ID (kid) exists in JWKS
- [ ] User exists in database
- [ ] User account is active (`is_active = true`)

## Debug Endpoint Usage

### Example Request

```bash
curl -X GET \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://localhost:8000/debug/token
```

### Example Response (Success)

```json
{
  "token_present": true,
  "config": {
    "clerk_issuer": "https://clerk.counterforce-hero.tech",
    "clerk_jwks_url": "https://clerk.counterforce-hero.tech/.well-known/jwks.json",
    "clerk_audience": null,
    "clerk_publishable_key_prefix": "pk_test_..."
  },
  "token_info": {
    "header": {
      "alg": "RS256",
      "kid": "abc123..."
    },
    "claims": {
      "iss": "https://clerk.counterforce-hero.tech",
      "aud": null,
      "sub": "user_abc123",
      "email": "user@example.com",
      "exp": 1234567890,
      "iat": 1234567890
    },
    "issuer_match": true,
    "audience_match": null
  },
  "verification_result": {
    "status": "success",
    "verified_claims": {
      "sub": "user_abc123",
      "email": "user@example.com",
      "iss": "https://clerk.counterforce-hero.tech"
    }
  },
  "error": null
}
```

### Example Response (Failure)

```json
{
  "token_present": true,
  "config": {
    "clerk_issuer": "https://clerk.counterforce-hero.tech",
    "clerk_jwks_url": "https://clerk.counterforce-hero.tech/.well-known/jwks.json",
    "clerk_audience": null
  },
  "token_info": {
    "header": {...},
    "claims": {
      "iss": "https://different-issuer.com",
      ...
    },
    "issuer_match": false
  },
  "verification_result": {
    "status": "failed",
    "error": "Invalid token issuer. Expected: https://clerk.counterforce-hero.tech",
    "status_code": 401
  },
  "error": null
}
```

## Next Steps

1. **Run the debug endpoint** with your token to see detailed information
2. **Check server logs** for specific error messages
3. **Verify environment variables** match your Clerk configuration
4. **Test with a fresh token** from Clerk to rule out token expiration
5. **Check user status** in the database if token verification succeeds but you still get 403

## Additional Resources

- [Clerk JWT Verification Docs](https://clerk.com/docs/backend-requests/handling/manual-jwt)
- [Clerk API Keys](https://clerk.com/docs/keys/overview)
- [JWKS Specification](https://tools.ietf.org/html/rfc7517)
