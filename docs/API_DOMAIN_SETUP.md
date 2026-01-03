# API Domain Setup Guide

This guide sets up a dedicated API domain (`api.counterforce-hero.tech`) that routes directly to the backend, eliminating Next.js proxy complexity and token passing issues.

## Benefits

- ✅ Direct API calls from frontend to backend
- ✅ No Next.js rewrite/proxy complexity
- ✅ Proper CORS handling
- ✅ Cleaner token passing
- ✅ Better separation of concerns

## Step 1: Update Cloudflare Tunnel Configuration

On the mac-mini production server:

```bash
# SSH to mac-mini
ssh mac-mini

# Edit the Cloudflare tunnel config
nano ~/.cloudflared/config.yml
```

Update the config to include both frontend and API routes:

```yaml
tunnel: <YOUR_TUNNEL_ID>
credentials-file: /Users/jforrest/.cloudflared/<TUNNEL_ID>.json

ingress:
  # Frontend (Next.js)
  - hostname: library.counterforce-hero.tech
    service: http://localhost:3400

  # Backend API (FastAPI)
  - hostname: api.counterforce-hero.tech
    service: http://localhost:8400

  # Catch-all (must be last)
  - service: http_status:404
```

**Important:** The catch-all route (`http_status:404`) must be the last entry.

## Step 2: Add DNS Record in Cloudflare

1. Go to Cloudflare Dashboard → Your domain (`counterforce-hero.tech`)
2. Navigate to **DNS** → **Records**
3. Click **Add record**
4. Configure:
   - **Type**: CNAME
   - **Name**: `api`
   - **Target**: `<YOUR_TUNNEL_ID>.cfargotunnel.com`
   - **Proxy status**: Proxied (orange cloud) ✅
5. Click **Save**

## Step 3: Restart Cloudflare Tunnel

```bash
# On mac-mini
launchctl unload ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist
launchctl load ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist

# Verify it's running
ps aux | grep cloudflared | grep -v grep

# Check logs
tail -f /tmp/cloudflared.log
```

## Step 4: Update Frontend Environment

Update the production frontend `.env.local`:

```bash
# On mac-mini
cd ~/production/hero-evidence-library/frontend/nextjs-app

cat > .env.local << 'EOF'
# Use dedicated API domain in production
NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech
# BACKEND_URL is only for Next.js server-side rewrites (optional, not used with dedicated API domain)
# If kept, should be http://localhost:8400 (server-to-server communication, no HTTPS needed)
BACKEND_URL=http://localhost:8400
EOF
```

## Step 5: Update Frontend Code

Update `lib/api.ts` to use the API domain in production:

```typescript
// Use dedicated API domain in production, localhost in development
const API_URL =
  typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? process.env.NEXT_PUBLIC_API_URL || "https://api.counterforce-hero.tech"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8400";
```

## Step 6: Remove Next.js Rewrites (Optional)

Since we're using a dedicated API domain, we can remove the Next.js rewrites:

```javascript
// In next.config.js - you can remove or comment out the rewrites:
async rewrites() {
  // No longer needed - using dedicated API domain
  // const backendUrl = process.env.BACKEND_URL || 'http://localhost:8400';
  // return [
  //   {
  //     source: '/api/:path*',
  //     destination: `${backendUrl}/api/:path*`,
  //   },
  // ];
  return [];
},
```

## Step 7: Rebuild and Redeploy

```bash
# From your dev machine
./deploy.sh
```

## Step 8: Verify Setup

1. **Test API domain directly:**

   ```bash
   curl https://api.counterforce-hero.tech/docs
   # Should show FastAPI docs
   ```

2. **Test from browser:**

   - Open `https://library.counterforce-hero.tech`
   - Check Network tab - API calls should go to `api.counterforce-hero.tech`
   - Verify tokens are being sent in Authorization headers

3. **Check CORS:**
   - Backend already allows all origins (`allow_origins=["*"]`)
   - Should work automatically

## Troubleshooting

### API domain not resolving

- Check DNS record in Cloudflare (should be proxied)
- Verify tunnel config has the API route
- Restart tunnel: `launchctl unload ... && launchctl load ...`

### CORS errors

- Backend CORS is already configured to allow all origins
- If issues persist, check browser console for specific CORS error

### 401 errors persist

- Check that tokens are being sent (Network tab → Headers)
- Verify backend can reach Clerk JWKS endpoint
- Use `/debug/token` endpoint to test token verification

## Architecture After Setup

```
Browser
  ↓
library.counterforce-hero.tech (Cloudflare Tunnel)
  ↓
localhost:3400 (Next.js Frontend)
  ↓ (API calls)
api.counterforce-hero.tech (Cloudflare Tunnel)
  ↓
localhost:8400 (FastAPI Backend)
```

## Benefits Achieved

- ✅ Frontend makes direct API calls to `api.counterforce-hero.tech`
- ✅ No Next.js proxy/rewrite complexity
- ✅ Tokens passed directly in Authorization headers
- ✅ Clean separation: frontend domain vs API domain
- ✅ Easier debugging (direct API access)
- ✅ Better for API documentation (accessible at api.counterforce-hero.tech/docs)
