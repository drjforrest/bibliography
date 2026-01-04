# Inviting Users to the Application

This application is **invite-only**. Users must be manually created in the database before they can sign in via Clerk.

## Overview

The authentication flow works as follows:

1. **Admin invites user**: An administrator runs the invite script to create a user record in the database
2. **User signs in via Clerk**: The user signs in through Clerk's authentication UI
3. **Backend verifies**: The backend verifies the Clerk JWT token and looks up the user by `clerk_user_id` or `email`
4. **Access granted**: If the user exists in the database, they can access the application

If a user tries to sign in via Clerk but doesn't exist in the database, they will receive a **403 Forbidden** error with the message: "Access denied. This is an invite-only application. Please contact an administrator to request access."

## How to Invite a User

### Step 1: Get the Clerk User ID

You need the user's Clerk User ID. You can find this in the Clerk Dashboard:

1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Navigate to **Users**
3. Find the user (or create them if they don't exist yet)
4. Copy the **User ID** (format: `user_abc123xyz...`)

**Note**: If the user doesn't exist in Clerk yet, you can either:
- Create them in Clerk first, then invite them here
- Invite them here first, then they'll create their Clerk account when they sign in

### Step 2: Run the Invite Script

```bash
cd backend

# Basic invite (email + Clerk user ID required)
python scripts/invite_user_clerk.py \
    --email user@example.com \
    --clerk-user-id user_abc123xyz

# Full invite with profile information
python scripts/invite_user_clerk.py \
    --email user@example.com \
    --clerk-user-id user_abc123xyz \
    --first-name John \
    --last-name Doe \
    --avatar-url https://example.com/avatar.jpg
```

### Step 3: User Signs In

Once the user is created in the database, they can:
1. Go to the application URL
2. Click "Sign In"
3. Authenticate via Clerk (email/password, OAuth, etc.)
4. Access the application

## Listing Users

To see all users in the database:

```bash
cd backend
python scripts/invite_user_clerk.py --list
```

This will show:
- Email address
- Clerk User ID (or "Not linked" if missing)
- Display Name
- Active status

## Linking Existing Users

If you have existing users in the database that need to be linked to Clerk:

```bash
cd backend
python scripts/link_user_to_clerk.py \
    --email user@example.com \
    --clerk-user-id user_abc123xyz
```

## Workflow Examples

### Example 1: New User Invitation

1. User requests access: "I'd like to use the library"
2. Admin creates user in Clerk Dashboard (optional, can be done later)
3. Admin runs invite script:
   ```bash
   python scripts/invite_user_clerk.py \
       --email newuser@example.com \
       --clerk-user-id user_new123
   ```
4. Admin notifies user: "You've been invited! Sign in at https://library.counterforce-hero.tech"
5. User signs in via Clerk and gains access

### Example 2: Bulk Invitation

For inviting multiple users, you can create a simple script:

```bash
#!/bin/bash
# invite_multiple.sh

python scripts/invite_user_clerk.py --email alice@example.com --clerk-user-id user_alice123
python scripts/invite_user_clerk.py --email bob@example.com --clerk-user-id user_bob456
python scripts/invite_user_clerk.py --email charlie@example.com --clerk-user-id user_charlie789
```

## Troubleshooting

### User gets "403 Forbidden" after signing in

**Cause**: User exists in Clerk but not in the database.

**Solution**: Run the invite script to create the user:
```bash
python scripts/invite_user_clerk.py \
    --email user@example.com \
    --clerk-user-id <their_clerk_user_id>
```

### "User with email X already exists"

**Cause**: User already exists in the database.

**Solution**: 
- If they're not linked to Clerk, use `link_user_to_clerk.py`
- If they're already linked, no action needed - they can sign in

### "User with Clerk ID X already exists"

**Cause**: Another user is already linked to that Clerk ID.

**Solution**: Check the existing user's email and verify the Clerk ID is correct.

## Security Notes

- Users created via the invite script are automatically set to:
  - `is_active=True`
  - `is_verified=True` (Clerk handles email verification)
  - `is_superuser=False` (unless manually changed)
- **Password field**: A random password is generated but **never used or checked**. This is required by the `fastapi-users` library's base table structure (`SQLAlchemyBaseUserTableUUID`), which includes a `hashed_password` column that cannot be NULL. Since Clerk handles all authentication, this password is just a placeholder to satisfy the database schema constraint.
- The `clerk_user_id` field is unique and indexed for fast lookups

