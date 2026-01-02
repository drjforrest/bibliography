# JWT Authentication Implementation Summary

## ⚠️ Note: Legacy Documentation

**This document describes the legacy custom JWT authentication system.** The application has since migrated to **Clerk** for authentication.

**For current authentication setup, see:** [`CLERK_INTEGRATION_GUIDE.md`](./CLERK_INTEGRATION_GUIDE.md)

**Current Status:** The application uses Clerk, which automatically handles token refresh. No manual token refresh implementation is needed.

---

## Overview (Legacy System)

Simple JWT (JSON Web Token) authentication system for internal lab use, integrated with the FastAPI backend.

## Components Implemented (Legacy)

### 1. Authentication Context (`contexts/AuthContext.tsx`)

**Purpose**: Global authentication state management

**Features**:

- User state management
- JWT token storage (localStorage)
- Login/logout/register functions
- User profile access

**Note:** Token refresh was not implemented in the custom AuthContext. The system relied on backend token expiration and frontend logout on 401 errors.

**Key Functions**:

```typescript
login(email, password); // Authenticate user
register(name, email, password); // Create new account
logout(); // Clear session
refreshUser(); // Update user info
```

### 2. Protected Route Component (`components/ProtectedRoute.tsx`)

**Purpose**: Restrict access to authenticated users only

**Behavior**:

- Shows loading spinner while checking auth
- Redirects to `/auth/login` if not authenticated
- Renders protected content if authenticated

**Usage**:

```tsx
<ProtectedRoute>
  <YourProtectedContent />
</ProtectedRoute>
```

### 3. Login Page (`app/auth/login/page.tsx`)

**Features**:

- Email/password form
- Loading states
- Error handling
- Auto-redirect if already logged in
- Link to registration page

**Styling**:

- Gradient background
- Centered card layout
- Dark mode support
- Form validation

### 4. Registration Page (`app/auth/register/page.tsx`)

**Features**:

- Name, email, password fields
- Password confirmation
- Minimum 8-character validation
- Auto-login after registration
- Link to login page

**Validation**:

- Password match check
- Password length requirement
- Required fields

### 5. Updated Components

#### Sidebar (`components/layout/Sidebar.tsx`)

- Displays logged-in user info
- Avatar with fallback to initials
- Dropdown menu with logout
- User email display

#### Header (`components/layout/Header.tsx`)

- User avatar button
- Dropdown profile menu
- Logout option
- Consistent with sidebar

### 6. Protected Pages

All main pages now wrapped with `ProtectedRoute`:

- `/` - Library home
- `/papers/[paperId]` - Annotation screen
- `/messages` - Message board

### 7. API Client Updates (`lib/api.ts`)

**Already configured for JWT**:

- Automatic token injection in headers
- 401 error handling (logout on unauthorized)
- Token stored in localStorage
- Axios interceptors for auth

## Authentication Flow

### Registration Flow

1. User visits `/auth/register`
2. Fills name, email, password
3. Frontend validates password match & length
4. POST to `/api/v1/auth/register`
5. Auto-login after successful registration
6. Redirect to `/` (library home)

### Login Flow

1. User visits `/auth/login` (or redirected from protected route)
2. Enters email & password
3. POST to `/api/v1/auth/jwt/login` (OAuth2 form data)
4. Backend returns `access_token`
5. Frontend fetches user info from `/api/v1/users/me`
6. Token & user stored in localStorage
7. Redirect to `/` (library home)

### Protected Route Access

1. User navigates to protected page
2. `ProtectedRoute` checks for token & user
3. If missing: redirect to `/auth/login`
4. If present: render protected content

### Logout Flow

1. User clicks "Sign out" in dropdown
2. Clear token & user from localStorage
3. Reset auth context state
4. Redirect to `/auth/login`

## Security Considerations

### Client-Side

- JWT stored in localStorage (simple for lab use)
- Tokens included in Authorization header
- Auto-logout on 401 responses
- No sensitive data in client state

### Backend Integration

Expects FastAPI with:

- `/api/v1/auth/jwt/login` - OAuth2 password flow
- `/api/v1/auth/register` - User registration
- `/api/v1/users/me` - Current user endpoint
- JWT Bearer token authentication

**HTTPS Requirement**: HTTPS is required in all environments (localhost development excepted) to prevent token interception during transmission.

### For Lab Environment

- ✅ Simple & sufficient for trusted network
- ✅ Easy to implement & maintain
- ✅ Standard JWT approach
- ⚠️ Not for public internet (consider httpOnly cookies for that)

## Token Management

**Storage**: localStorage

- Key: `auth_token`
- Value: JWT string

**User Data**: localStorage

- Key: `user`
- Value: JSON serialized user object

**Token Refresh**: Not implemented in legacy system

- Tokens loaded from localStorage on mount
- Frontend validates on protected route access
- No automatic refresh - relies on backend token expiration

**Expiration**: Handled by backend

- Frontend logs out on 401 errors
- Backend controls token TTL
- Users must re-authenticate when tokens expire

## Testing Checklist

- [x] Registration creates account
- [x] Login authenticates user
- [x] Protected routes redirect when not authenticated
- [x] Logout clears session
- [x] User info displays in sidebar/header
- [x] Token persists across page refreshes
- [x] Dark mode works on auth pages
- [x] Error messages display correctly
- [x] Build succeeds with no TypeScript errors

## Future Enhancements (Optional)

**Note:** These enhancements were planned for the legacy system. The migration to Clerk has addressed many of these concerns:

- ✅ **Token Refresh**: Now handled automatically by Clerk
- ✅ **Session Management**: Managed by Clerk
- ✅ **Security**: Enhanced through Clerk's infrastructure

Remaining optional enhancements for the legacy system (if not using Clerk):

1. **Session Management**

   - Remember me checkbox
   - Session timeout warnings

2. **Security Hardening**

   - httpOnly cookies instead of localStorage
   - CSRF protection
   - Rate limiting on login attempts

3. **User Management**

   - Password reset flow
   - Email verification
   - Profile editing

4. **Admin Features**
   - User management dashboard
   - Role-based permissions
   - Activity logs

## API Endpoints Used

```
POST   /api/v1/auth/jwt/login       # Login
POST   /api/v1/auth/register        # Register
GET    /api/v1/users/me            # Get current user
```

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Files Modified/Created

**New Files**:

- `contexts/AuthContext.tsx`
- `components/ProtectedRoute.tsx`
- `app/auth/login/page.tsx`
- `app/auth/register/page.tsx`

**Modified Files**:

- `app/layout.tsx` - Added AuthProvider
- `app/page.tsx` - Wrapped with ProtectedRoute
- `app/papers/[paperId]/page.tsx` - Wrapped with ProtectedRoute
- `app/messages/page.tsx` - Wrapped with ProtectedRoute
- `components/layout/Sidebar.tsx` - Added user menu
- `components/layout/Header.tsx` - Added user menu

## Conclusion

The authentication system is production-ready for internal lab use. It provides:

✅ Secure JWT-based authentication
✅ User registration & login
✅ Protected routes
✅ Session persistence
✅ Clean user interface
✅ Dark mode support
✅ TypeScript type safety

The system is simple enough for a home server deployment while being robust enough for a research lab environment.
