# Clerk Authentication Migration Plan

## Overview

Migrating from custom JWT (fastapi-users) authentication to Clerk for improved security, user experience, and feature set.

## Current Authentication Stack

### Backend (FastAPI)
- **Library**: `fastapi-users`
- **Method**: JWT Bearer tokens
- **Token Lifetime**: 30 days
- **Storage**: Custom User model in PostgreSQL
- **Endpoints**:
  - `POST /auth/jwt/login` - Login with email/password
  - `POST /auth/register` - User registration
  - `POST /auth/forgot-password` - Password reset
  - `GET /users/me` - Get current user
  - Optional: Google OAuth

### Frontend (Next.js)
- **Auth Context**: Custom React context (`AuthContext.tsx`)
- **Token Storage**: localStorage (`auth_token`, `user`)
- **API Client**: Axios with Bearer token interceptor
- **Login Flow**: Email/password form → JWT token → localStorage

## Why Clerk?

1. **Security**: Industry-standard authentication with automatic security updates
2. **User Experience**: Pre-built UI components, magic links, social OAuth
3. **Features**: MFA, session management, user profiles, organizations
4. **Maintenance**: Reduces custom auth code by ~80%
5. **Compliance**: SOC 2 Type II, GDPR, CCPA compliant

## Migration Strategy

### Phase 1: Clerk Setup (30 minutes)

1. **Create Clerk Application**
   - Sign up at https://clerk.com
   - Create new application
   - Configure allowed callback URLs:
     - Development: `http://localhost:3000/`
     - Production: `https://library.counterforce-hero.tech/`

2. **Get API Keys**
   - Publishable Key (Frontend): `pk_test_...` or `pk_live_...`
   - Secret Key (Backend): `sk_test_...` or `sk_live_...`
   - JWT Verification Key: From Clerk Dashboard → API Keys → Advanced

3. **Configure Clerk Settings**
   - Enable email/password authentication
   - Configure email provider (or use Clerk's)
   - Set up user profile fields
   - Optional: Enable Google OAuth

### Phase 2: Frontend Migration (1-2 hours)

#### Install Dependencies

```bash
cd frontend/nextjs-app
npm install @clerk/nextjs
```

#### Replace Authentication Components

**Files to Modify:**
1. `app/layout.tsx` - Wrap app with ClerkProvider
2. `contexts/AuthContext.tsx` - Replace with Clerk hooks
3. `app/auth/login/page.tsx` - Replace with Clerk SignIn
4. `app/auth/register/page.tsx` - Replace with Clerk SignUp
5. `components/ProtectedRoute.tsx` - Use Clerk auth checking
6. `lib/api.ts` - Update to use Clerk session tokens

**New Structure:**

```typescript
// app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs'

export default function RootLayout({ children }) {
  return (
    <ClerkProvider>
      <html>
        <body>{children}</body>
      </html>
    </ClerkProvider>
  )
}

// app/auth/sign-in/[[...sign-in]]/page.tsx
import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return <SignIn routing="path" path="/auth/sign-in" />
}

// contexts/AuthContext.tsx (simplified or removed)
import { useUser, useAuth as useClerkAuth } from '@clerk/nextjs'

export function useAuth() {
  const { user, isLoaded } = useUser()
  const { getToken } = useClerkAuth()

  return {
    user,
    isLoading: !isLoaded,
    isAuthenticated: !!user,
    getToken, // Use this to get JWT for API calls
  }
}

// lib/api.ts (update interceptor)
this.client.interceptors.request.use(
  async (config) => {
    if (typeof window !== 'undefined') {
      // Get Clerk session token
      const { getToken } = await import('@clerk/nextjs')
      const token = await getToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  }
)
```

### Phase 3: Backend Migration (1-2 hours)

#### Install Dependencies

```bash
cd backend
pip install pyjwt cryptography requests
```

#### Create Clerk JWT Verification

**New File: `backend/app/auth/clerk.py`**

```python
import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
from typing import Optional
from app.config import config

security = HTTPBearer()

@lru_cache()
def get_clerk_jwks():
    """Fetch and cache Clerk's JWKS (JSON Web Key Set)"""
    response = requests.get(f"https://{config.CLERK_FRONTEND_API}/.well-known/jwks.json")
    return response.json()

def verify_clerk_token(token: str) -> dict:
    """Verify Clerk JWT token"""
    try:
        jwks = get_clerk_jwks()

        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)

        # Find the right key
        key = None
        for jwk_key in jwks["keys"]:
            if jwk_key["kid"] == unverified_header["kid"]:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk_key)
                break

        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: key not found"
            )

        # Verify and decode token
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=config.CLERK_FRONTEND_API,  # or your specific audience
            options={"verify_exp": True}
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current user from Clerk JWT"""
    token = credentials.credentials
    payload = verify_clerk_token(token)

    # Clerk JWT payload contains user ID in 'sub' claim
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no user ID"
        )

    # Get or create user in database
    from app.db import get_async_session, User
    from sqlalchemy import select

    async for session in get_async_session():
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Create user from Clerk data
            user = User(
                id=user_id,
                email=payload.get("email"),
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user
```

#### Update App Routes

**File: `backend/app/app.py`**

```python
# Remove old fastapi-users routes
# from app.users import fastapi_users, auth_backend
# app.include_router(fastapi_users.get_auth_router(...))

# Add simple verify endpoint for frontend
from app.auth.clerk import get_current_user

@app.get("/auth/verify")
async def verify_auth(user = Depends(get_current_user)):
    """Verify authentication and return user info"""
    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    }
```

#### Update All Protected Routes

Replace `current_active_user` dependency with `get_current_user`:

```python
# Before
from app.users import current_active_user

@router.get("/papers")
async def get_papers(user = Depends(current_active_user)):
    pass

# After
from app.auth.clerk import get_current_user

@router.get("/papers")
async def get_papers(user = Depends(get_current_user)):
    pass
```

### Phase 4: Environment Configuration

#### Frontend `.env.local`

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/auth/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/auth/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Backend `.env`

```bash
CLERK_FRONTEND_API=your-app.clerk.accounts.dev
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...
```

### Phase 5: User Migration (Optional)

If you want to migrate existing users from fastapi-users to Clerk:

#### Option A: Bulk Import via Clerk API

1. Export users from PostgreSQL
2. Use Clerk's User API to create users
3. Users receive "set password" email

#### Option B: Gradual Migration

1. Keep both auth systems temporarily
2. On first Clerk login, link accounts by email
3. Deprecate old auth after migration period

**Recommended: Option B** for zero downtime

### Phase 6: Testing & Deployment

#### Local Testing

1. Start backend with Clerk auth
2. Start frontend with Clerk components
3. Test flows:
   - [ ] Sign up new user
   - [ ] Sign in existing user
   - [ ] Access protected routes
   - [ ] API calls with Clerk tokens
   - [ ] Sign out

#### Production Deployment

1. Update production environment variables
2. Deploy backend with Clerk verification
3. Deploy frontend with Clerk components
4. Update Clerk dashboard with production URLs
5. Test production authentication

## Files to Modify

### Frontend Changes

```
frontend/nextjs-app/
├── package.json                              # Add @clerk/nextjs
├── .env.local                                # Add Clerk keys
├── app/layout.tsx                            # Wrap with ClerkProvider
├── app/auth/sign-in/[[...sign-in]]/page.tsx  # NEW - Clerk sign in
├── app/auth/sign-up/[[...sign-up]]/page.tsx  # NEW - Clerk sign up
├── contexts/AuthContext.tsx                  # Simplify or remove
├── components/ProtectedRoute.tsx             # Use Clerk auth
├── lib/api.ts                                # Update token retrieval
└── middleware.ts                             # NEW - Clerk middleware (optional)
```

### Backend Changes

```
backend/
├── requirements.txt                          # Add pyjwt, cryptography
├── .env                                      # Add Clerk keys
├── app/
│   ├── auth/
│   │   ├── __init__.py                      # NEW
│   │   └── clerk.py                         # NEW - Clerk verification
│   ├── app.py                               # Remove fastapi-users routes
│   ├── users.py                             # DEPRECATED - can remove
│   └── routes/
│       ├── *.py                             # Update all to use get_current_user
│       └── user_routes.py                   # Simplify or remove
```

## Rollback Plan

If migration fails:

1. **Frontend**: Revert to previous commit, redeploy
2. **Backend**: Restore old auth routes, redeploy
3. **Database**: No changes needed (User table compatible)
4. **Clerk**: Delete application (free tier)

## Timeline

- **Phase 1 (Setup)**: 30 minutes
- **Phase 2 (Frontend)**: 1-2 hours
- **Phase 3 (Backend)**: 1-2 hours
- **Phase 4 (Config)**: 15 minutes
- **Phase 5 (Testing)**: 30 minutes
- **Phase 6 (Deploy)**: 30 minutes

**Total Estimated Time**: 4-6 hours

## Benefits Post-Migration

1. **Reduced Code**: Remove ~500 lines of custom auth code
2. **Better UX**: Professional sign-in/up UI, magic links
3. **Security**: Automatic security updates, MFA support
4. **Features**: User profiles, organizations, webhooks
5. **Maintenance**: Zero auth maintenance required

## Next Steps

1. Review this plan
2. Create Clerk account
3. Run local migration
4. Test thoroughly
5. Deploy to production

Would you like me to proceed with the implementation?
