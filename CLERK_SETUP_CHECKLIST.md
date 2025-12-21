# Clerk Integration Setup Checklist

Follow these steps to complete your Clerk authentication integration.

## ✅ Pre-Setup (Completed)

- [x] Clerk package installed in frontend (`@clerk/nextjs`)
- [x] Clerk middleware configured in [`frontend/nextjs-app/middleware.ts`](frontend/nextjs-app/middleware.ts:1)
- [x] ClerkProvider added to [`frontend/nextjs-app/app/layout.tsx`](frontend/nextjs-app/app/layout.tsx:1)
- [x] Backend services created
- [x] Database migration script created
- [x] Webhook handler implemented
- [x] API client updated for Clerk tokens

## 🔧 Setup Steps (Action Required)

### Step 1: Get Clerk Credentials

1. **Create Clerk Account**

   - Go to [https://clerk.com](https://clerk.com)
   - Sign up for a free account

2. **Create Application**

   - Click "Add application"
   - Name it "Hero Evidence Library"
   - Choose authentication methods (Email, Google, etc.)

3. **Get API Keys**

   - Go to "API Keys" in sidebar
   - Copy **Publishable key** (starts with `pk_test_`)
   - Copy **Secret key** (starts with `sk_test_`)

4. **Create Webhook**
   - Go to "Webhooks" in sidebar
   - Click "Add Endpoint"
   - **Endpoint URL**: `http://your-backend-domain/webhooks/clerk`
     - For local dev: Use ngrok (see below)
   - **Subscribe to events**:
     - ✅ `user.created`
     - ✅ `user.updated`
     - ✅ `user.deleted`
   - Copy **Signing Secret** (starts with `whsec_`)

### Step 2: Configure Environment Variables

**Backend** - Create/Edit `backend/.env`:

```bash
# Add these lines (replace with your actual Clerk keys from dashboard)
CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=
CLERK_WEBHOOK_SECRET=
```

**Frontend** - Create/Edit `frontend/nextjs-app/.env.local`:

```bash
# Add these lines (replace with your actual Clerk keys from dashboard)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
```

### Step 3: Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend (already installed)
cd frontend/nextjs-app
npm install
```

### Step 4: Run Database Migration

```bash
cd backend
python scripts/add_clerk_user_id_migration.py
```

Expected output:

```
Starting Clerk migration...
Adding clerk_user_id column to user table...
✓ Successfully added clerk_user_id column and index

✓ Migration completed successfully!
```

### Step 5: Setup Local Development (ngrok for webhooks)

For local testing, expose your backend:

```bash
# Install ngrok (one time)
brew install ngrok  # macOS
# OR download from https://ngrok.com

# Run ngrok
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and use it in Clerk:

- **Webhook URL**: `https://abc123.ngrok.io/webhooks/clerk`

### Step 6: Start Applications

**Terminal 1 - Backend:**

```bash
cd backend
uvicorn app.app:app --reload --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend/nextjs-app
npm run dev
```

## 🧪 Testing Checklist

### Test 1: Sign Up Flow

- [ ] Visit `http://localhost:3000`
- [ ] Click "Sign up"
- [ ] Create account with email/password
- [ ] Verify redirect back to app
- [ ] Check database for new user with `clerk_user_id`

### Test 2: Sign In Flow

- [ ] Sign out from app
- [ ] Click "Sign in"
- [ ] Enter credentials
- [ ] Verify successful login
- [ ] Check that user info displays in sidebar/header

### Test 3: Webhook Sync

- [ ] Check backend logs for webhook events
- [ ] Verify user was created in database
- [ ] Update profile in Clerk Dashboard
- [ ] Check database for updated info

### Test 4: API Authentication

- [ ] Open browser DevTools → Network tab
- [ ] Make an API request (e.g., view papers)
- [ ] Check request headers for `Authorization: Bearer <token>`
- [ ] Verify request succeeds (200 status)

### Test 5: Protected Routes

- [ ] Sign out
- [ ] Try to access `/dashboard` or `/`
- [ ] Verify redirect to sign-in page
- [ ] Sign in
- [ ] Verify access granted

### Test 6: Token Validation

Visit backend docs:

```bash
# Test protected endpoint
curl -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  http://localhost:8000/api/v1/me
```

## 🔍 Verification Commands

```bash
# Check if clerk_user_id column exists
psql -d your_database -c "SELECT column_name FROM information_schema.columns WHERE table_name='user' AND column_name='clerk_user_id';"

# Check webhook endpoint is accessible
curl http://localhost:8000/webhooks/clerk/test

# Expected response:
# {"message":"Clerk webhook endpoint is active","configured":true}
```

## 🐛 Troubleshooting

### Issue: "Clerk webhook secret not configured"

**Solution**: Add `CLERK_WEBHOOK_SECRET` to backend `.env` file

### Issue: Webhooks not working locally

**Solution**: Use ngrok to expose backend, update webhook URL in Clerk

### Issue: "Invalid token" errors

**Solution**:

1. Verify `CLERK_SECRET_KEY` matches in both frontend and backend
2. Clear browser cache and sign out/in again
3. Check token hasn't expired

### Issue: Users not being created

**Solution**:

1. Check backend logs for errors
2. Verify migration ran successfully
3. Test webhook endpoint: `curl http://localhost:8000/webhooks/clerk/test`

### Issue: Frontend can't connect to backend

**Solution**:

1. Verify `NEXT_PUBLIC_API_URL=http://localhost:8000` in frontend `.env.local`
2. Check CORS is enabled in backend
3. Restart both services

## 📚 Additional Resources

- **Full Guide**: See [`CLERK_INTEGRATION_GUIDE.md`](CLERK_INTEGRATION_GUIDE.md:1)
- **Example Routes**: See [`backend/app/routes/example_clerk_auth.py`](backend/app/routes/example_clerk_auth.py:1)
- **Clerk Docs**: [https://clerk.com/docs](https://clerk.com/docs)
- **Support**: [https://clerk.com/discord](https://clerk.com/discord)

## 🎯 Next Steps After Setup

1. **Customize Clerk UI**

   - Go to Clerk Dashboard → Customization
   - Match your app's branding
   - Upload logo

2. **Add Social Providers**

   - Enable Google, GitHub, etc. in Clerk Dashboard
   - Configure OAuth credentials

3. **Update Existing Routes**

   - Replace `current_active_user` with `require_clerk_auth`
   - See [`example_clerk_auth.py`](backend/app/routes/example_clerk_auth.py:1) for examples

4. **Production Deployment**
   - Use production Clerk keys (`pk_live_`, `sk_live_`)
   - Update webhook URL to production backend
   - Enable JWKS verification in [`clerk_service.py`](backend/app/services/clerk_service.py:1)

## ✨ Summary

Your Clerk integration is ready! The files have been created and configured. You just need to:

1. Get your Clerk credentials from dashboard.clerk.com
2. Add them to your `.env` files
3. Run the database migration
4. Start your apps and test!

For detailed instructions, see [`CLERK_INTEGRATION_GUIDE.md`](CLERK_INTEGRATION_GUIDE.md:1)
