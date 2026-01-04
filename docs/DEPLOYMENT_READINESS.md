# Deployment Readiness Checklist

## ✅ Environment Variables Verification

### Backend `.env.production` Status

**Location**: `.env.production` (project root)

**Clerk Variables Found**:
- ✅ `AUTH_TYPE="clerk"` - Authentication type set
- ✅ `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Publishable key (for frontend)
- ✅ `CLERK_SECRET_KEY` - Secret key (for backend)
- ✅ `CLERK_FRONTEND_API_URL` - Frontend API URL (used as CLERK_ISSUER fallback)
- ✅ `CLERK_JWKS_URL` - JWKS endpoint URL
- ✅ `CLERK_WEBHOOK_SECRET` - Webhook signing secret ✅ **ADDED**

### Deployment Process

The `deploy.sh` script will:

1. **Copy `.env.production` to server**:
   - Copies `.env.production` → `backend/.env.template` on server
   - If `.env.production.local` exists, merges both files
   - Otherwise, copies `.env.template` → `backend/.env` on server

2. **Result**: Your `.env.production` will become `backend/.env` on the production server

### Code Compatibility

✅ **All Clerk variables are correctly mapped**:
- `CLERK_SECRET_KEY` → `CLERK_API_KEY` (internal name)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` → `CLERK_PUBLISHABLE_KEY` (fallback supported)
- `CLERK_FRONTEND_API_URL` → `CLERK_ISSUER` (fallback supported)
- `CLERK_JWKS_URL` → Direct match
- `CLERK_WEBHOOK_SECRET` → `CLERK_WEBHOOK_SIGNING_KEY` (internal name)

## Pre-Deployment Checklist

### ✅ Environment Variables
- [x] `.env.production` exists in project root
- [x] All Clerk variables are set
- [x] `CLERK_WEBHOOK_SECRET` is included
- [x] Webhook URL configured in Clerk Dashboard: `https://api.counterforce-hero.tech/webhooks/clerk`

### ⚠️ Optional: Separate Secrets File
If you want to keep secrets separate from the main `.env.production`:
- Create `.env.production.local` with sensitive values only
- The deploy script will merge both files on the server

### 🔍 Deployment Script Behavior

**What happens during deployment**:

```bash
# Step 1: Copy .env.production to server
scp .env.production → server:backend/.env.template

# Step 2: Create final .env on server
if .env.production.local exists:
    merge .env.template + .env.production.local → backend/.env
else:
    copy .env.template → backend/.env
```

**Result**: `backend/.env` on production server will contain all your variables from `.env.production`

## Ready to Deploy? ✅

**YES!** You're ready to deploy:

1. ✅ All Clerk environment variables are set
2. ✅ `CLERK_WEBHOOK_SECRET` is included
3. ✅ Code supports Clerk's export format
4. ✅ Deployment script will copy `.env.production` → `backend/.env`

### Deploy Command

```bash
./deploy.sh
```

The script will:
- Sync code to production server
- Copy `.env.production` to `backend/.env` on server
- Install dependencies
- Start backend and frontend services

## Post-Deployment Verification

After deployment, verify:

1. **Backend is running**:
   ```bash
   curl https://api.counterforce-hero.tech/api/v1/health
   ```

2. **Webhook endpoint is accessible**:
   ```bash
   curl https://api.counterforce-hero.tech/webhooks/clerk/test
   ```
   Should return: `{"message": "Clerk webhook endpoint is active"}`

3. **Check backend logs**:
   ```bash
   ssh mac-mini "tail -f ~/production/hero-evidence-library/hero_evidence_library_backend.log"
   ```

4. **Test authentication**:
   - Visit `https://library.counterforce-hero.tech`
   - Try signing in with Clerk
   - Verify user is created in database

## Notes

- **Typo in .env.production**: `CLERK_BACKEND_API_UERL` has a typo (UERL vs URL), but this variable is not used by the code, so it's harmless
- **Webhook Secret**: Make sure the webhook URL in Clerk Dashboard matches: `https://api.counterforce-hero.tech/webhooks/clerk`

