# Frontend Rebuild Instructions

## Issue
The `.env.local` file has been updated with the correct `NEXT_PUBLIC_API_URL`, but the build still has the old value embedded.

## Required Steps

Run these commands on the production server (mac-mini):

```bash
cd ~/production/hero-evidence-library/frontend/nextjs-app

# 1. Verify .env.local has correct value
cat .env.local | grep NEXT_PUBLIC_API_URL
# Should show: NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech

# 2. Clean build directory (CRITICAL - removes cached build)
rm -rf .next

# 3. Rebuild with correct environment variables
npm run build

# 4. Verify build completed successfully
ls -la .next/BUILD_ID
# Should show a new timestamp

# 5. Stop any existing frontend process
pkill -f "next.*3400"
# Wait a moment
sleep 2

# 6. Start frontend service
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
nvm use 22
nohup npm run start -- -p 3400 > ../../hero_evidence_library_frontend.log 2>&1 &

# 7. Verify it's running
sleep 2
ps aux | grep "next.*3400" | grep -v grep

# 8. Check logs for any errors
tail -20 ../../hero_evidence_library_frontend.log
```

## Verification

After rebuilding and restarting:

1. **Check browser Network tab** - API requests should go to `api.counterforce-hero.tech`, not `library.counterforce-hero.tech/api`

2. **Clear browser cache** - The browser might be caching the old JavaScript bundle:
   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)
   - Or clear browser cache for the site

3. **Verify API calls work** - Papers should load on the homepage

## If Still Not Working

If the issue persists after rebuild:

1. Check the actual JavaScript bundle:
   ```bash
   # Search for the API URL in the build
   grep -r "api.counterforce-hero.tech" .next/static/chunks/*.js | head -3
   ```

2. Check if there are multiple .env files:
   ```bash
   ls -la .env*
   # Should only have .env.local (and maybe .env.production.local)
   ```

3. Verify the build actually completed:
   ```bash
   tail -50 ../../hero_evidence_library_frontend.log
   # Look for build errors
   ```

