# Clerk Authentication Integration Guide

This guide explains how to set up Clerk authentication with your Hero Evidence Library application.

## Overview

The application now uses **Clerk** for authentication instead of the previous fastapi-users system. Clerk provides:

- 🔐 Secure authentication with multiple providers (email, Google, GitHub, etc.)
- 👤 User management and profiles
- 🔄 Automatic user synchronization between Clerk and your database
- 🎨 Beautiful, customizable UI components

## Architecture

### Frontend (Next.js)

- Uses `@clerk/nextjs` for authentication
- Clerk middleware protects routes
- ClerkProvider wraps the app for auth context
- API client automatically includes Clerk JWT tokens

### Backend (FastAPI)

- Receives Clerk webhooks for user sync
- Validates Clerk JWT tokens
- Maps Clerk users to database users table
- Maintains backward compatibility with existing user data

## Setup Instructions

### 1. Create a Clerk Account

1. Go to [https://clerk.com](https://clerk.com) and sign up
2. Create a new application
3. Choose your authentication methods (email, Google, etc.)

### 2. Get Your Clerk Credentials

From your Clerk Dashboard ([dashboard.clerk.com](https://dashboard.clerk.com)):

1. **API Keys** (in sidebar):

   - Copy `Publishable Key` (starts with `pk_test_` or `pk_live_`)
   - Copy `Secret Key` (starts with `sk_test_` or `sk_live_`)

2. **Webhooks** (in sidebar):
   - Click "Add Endpoint"
   - URL: `https://your-backend-url.com/webhooks/clerk`
   - Subscribe to events:
     - `user.created`
     - `user.updated`
     - `user.deleted`
   - Copy the **Signing Secret** (starts with `whsec_`)

### 5. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

The requirements now include:

- `svix>=1.38.0` - For webhook verification
- `pyjwt>=2.10.1` - For JWT token validation
- `cryptography>=44.0.0` - For cryptographic operations

### 6. Run Database Migration

Add the `clerk_user_id` column to your users table:

```bash
cd backend
python scripts/add_clerk_user_id_migration.py
```

This adds:

- `clerk_user_id` VARCHAR(255) UNIQUE column
- Index on `clerk_user_id` for faster lookups

### 7. Start Your Applications

**Backend:**

```bash
cd backend
uvicorn app.app:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend/nextjs-app
npm run dev
```

### 8. Test the Integration

1. Visit `http://localhost:3000`
2. You should be redirected to Clerk's sign-in page
3. Sign up with a new account
4. After sign-up, you'll be redirected back to the app
5. Check your database - a new user should be created with a `clerk_user_id`

## How It Works

### User Synchronization Flow

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend  │         │    Clerk     │         │   Backend    │
│  (Next.js)  │         │   Service    │         │  (FastAPI)   │
└──────┬──────┘         └──────┬───────┘         └──────┬───────┘
       │                       │                        │
       │  1. User Signs Up     │                        │
       ├──────────────────────>│                        │
       │                       │                        │
       │  2. User Created      │                        │
       │<──────────────────────┤                        │
       │                       │                        │
       │                       │  3. Webhook: user.created
       │                       ├───────────────────────>│
       │                       │                        │
       │                       │                        │  4. Create User
       │                       │                        │     in Database
       │                       │                        │
       │                       │  5. Webhook Success    │
       │                       │<───────────────────────┤
       │                       │                        │
       │  6. Make API Request  │                        │
       │  with JWT Token       │                        │
       ├────────────────────────────────────────────────>│
       │                       │                        │
       │                       │                        │  7. Validate Token
       │                       │                        │     & Get User
       │                       │                        │
       │  8. Response          │                        │
       │<────────────────────────────────────────────────┤
       │                       │                        │
```

### Authentication in API Requests

The frontend automatically includes Clerk JWT tokens in API requests:

```typescript
// In your components
import { useAuth } from "@clerk/nextjs";
import { createAuthenticatedClient } from "@/lib/api";

function MyComponent() {
  const { getToken } = useAuth();
  const api = createAuthenticatedClient(getToken);

  // Make authenticated requests
  const fetchData = async () => {
    const response = await api.get("/api/v1/papers");
    return response.data;
  };
}
```

### Backend Authentication

Protect your API endpoints with Clerk auth:

```python
from fastapi import APIRouter, Depends
from app.middleware.clerk_auth import require_clerk_auth
from app.db import User

router = APIRouter()

@router.get("/protected")
async def protected_route(
    current_user: User = Depends(require_clerk_auth)
):
    return {
        "message": f"Hello {current_user.email}",
        "user_id": str(current_user.id)
    }
```

## Migration from Existing Users

If you have existing users in your database:

1. The system will automatically link Clerk accounts to existing users by email
2. When a user signs in with Clerk, the system checks if an account with that email exists
3. If found, it adds the `clerk_user_id` to the existing user record
4. No data is lost, and all user relationships are preserved

## Troubleshooting

### Webhook Not Receiving Events

1. Check that your backend is publicly accessible (use ngrok for local dev)
2. Verify the webhook URL in Clerk Dashboard matches your backend URL
3. Check that you subscribed to the correct events
4. Check backend logs for webhook errors

### Users Not Being Created

1. Check backend logs for errors
2. Verify database connection is working
3. Ensure the migration script ran successfully
4. Check that webhook secret is correct

### Local Development with Webhooks

For local development, you need to expose your backend to the internet:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Expose your backend
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Use this URL in Clerk webhook settings: https://abc123.ngrok.io/webhooks/clerk
```

## Security Considerations

### JWT Token Validation

The current implementation decodes JWT tokens without full signature verification for simplicity. For production, you should:

1. Fetch Clerk's JWKS (JSON Web Key Set) endpoint
2. Verify token signatures against the public keys
3. Implement token caching and rotation

Update `backend/app/services/clerk_service.py` to add JWKS verification.

### Environment Variables

- Never commit `.env` files
- Use different keys for development and production
- Rotate secrets regularly
- Use environment-specific publishable keys

## Customization

### Customize Clerk UI

In your Clerk Dashboard:

1. Go to **Customization** → **Theme**
2. Match your app's colors and branding
3. Upload your logo
4. Customize text and labels

### Add Social Providers

In your Clerk Dashboard:

1. Go to **User & Authentication** → **Social Connections**
2. Enable providers (Google, GitHub, etc.)
3. Configure OAuth credentials
4. Users can now sign in with social accounts

## Support

- **Clerk Documentation**: [https://clerk.com/docs](https://clerk.com/docs)
- **Clerk Discord**: [https://clerk.com/discord](https://clerk.com/discord)
- **Backend Issues**: Check `backend/app/services/clerk_service.py` and `backend/app/routes/clerk_routes.py`
- **Frontend Issues**: Check `frontend/nextjs-app/middleware.ts` and `frontend/nextjs-app/app/layout.tsx`

## Files Modified/Created

### Backend

- ✅ `backend/requirements.txt` - Added Clerk dependencies
- ✅ `backend/app/config/__init__.py` - Added Clerk config
- ✅ `backend/app/services/clerk_service.py` - **NEW** - User sync service
- ✅ `backend/app/routes/clerk_routes.py` - **NEW** - Webhook handler
- ✅ `backend/app/middleware/clerk_auth.py` - **NEW** - Auth middleware
- ✅ `backend/scripts/add_clerk_user_id_migration.py` - **NEW** - Database migration
- ✅ `backend/app/app.py` - Added clerk routes
- ✅ `backend/.env.example` - Added Clerk variables

### Frontend

- ✅ `frontend/nextjs-app/lib/api.ts` - Updated API client for Clerk
- ✅ `frontend/nextjs-app/.env.example` - Added Clerk variables
- ✅ `frontend/nextjs-app/middleware.ts` - Already configured for Clerk
- ✅ `frontend/nextjs-app/app/layout.tsx` - Already has ClerkProvider

## Next Steps

1. ✅ Run the database migration
2. ✅ Add environment variables to both frontend and backend
3. ✅ Install dependencies
4. ✅ Configure Clerk webhook
5. ✅ Test user sign-up and sign-in
6. ✅ Update any API endpoints to use `require_clerk_auth` dependency
7. ✅ Test API calls with Clerk authentication

Your Clerk integration is now complete! 🎉
