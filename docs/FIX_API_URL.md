# Fix NEXT_PUBLIC_API_URL on Production

## Issue Found

The production `.env.local` file has:
```
NEXT_PUBLIC_API_URL=https://library.counterforce-hero.tech
```

But it should be:
```
NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech
```

This causes API calls to go through Next.js rewrites instead of directly to the API domain.

## Quick Fix

Run these commands on the production server (mac-mini):

```bash
cd ~/production/hero-evidence-library/frontend/nextjs-app

# Remove the incorrect line
sed -i.bak '/^NEXT_PUBLIC_API_URL=/d' .env.local

# Add the correct value
echo "NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech" >> .env.local

# Verify it's correct
cat .env.local | grep NEXT_PUBLIC_API_URL
# Should show: NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech

# Clean build (important - Next.js embeds env vars at build time)
rm -rf .next

# Rebuild
npm run build

# Restart frontend
pkill -f "next.*3400"
nohup npm run start -- -p 3400 > ../../hero_evidence_library_frontend.log 2>&1 &
```

## Verify Fix

After rebuilding, test in browser:
1. Open https://library.counterforce-hero.tech
2. Open DevTools → Network tab
3. Refresh page
4. Check API requests - they should go to `api.counterforce-hero.tech`, not `library.counterforce-hero.tech/api`

## Prevention

The `deploy.sh` script has been updated to automatically fix this on future deployments.

