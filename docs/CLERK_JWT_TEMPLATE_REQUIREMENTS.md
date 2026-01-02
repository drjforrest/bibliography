# Clerk JWT Template Requirements

## Required Claims for User Identification

Your Clerk JWT template must include the following claims to enable proper user authentication and user-specific content access:

### Required Claims

```json
{
  "sub": "{{user.id}}",
  "email": "{{user.primary_email_address}}",
  "given_name": "{{user.first_name}}",
  "family_name": "{{user.last_name}}",
  "picture": "{{user.image_url}}"
}
```

### Claim Usage

1. **`sub`** (Subject) - **REQUIRED**

   - Maps to `clerk_user_id` in the database
   - Primary identifier for finding/creating users
   - Always present in Clerk tokens by default

2. **`email`** - **REQUIRED**

   - Used for:
     - Linking existing users during migration
     - Creating new users with proper email addresses
     - Updating user information when email changes
   - **Without this, users cannot be properly identified for user-specific content**

3. **`given_name`** and **`family_name`** - Optional but recommended

   - Used to populate `display_name` field
   - Helps with user profile display

4. **`picture`** - Optional but recommended
   - Used for user avatar/profile image
   - Stored in `avatar_url` field

## How It Works

1. **Token Verification**: Backend verifies JWT using Clerk's JWKS
2. **User Lookup**: Uses `sub` (clerk_user_id) to find user in database
3. **User Creation/Linking**: If not found, tries to find by `email` (for migration), then creates new user
4. **User-Specific Queries**: All dashboard and user-specific routes use `user.id` (database UUID) to fetch user-specific content

## Example JWT Template Configuration

In Clerk Dashboard → JWT Templates → Your Template:

```json
{
  "sub": "{{user.id}}",
  "email": "{{user.primary_email_address}}",
  "given_name": "{{user.first_name}}",
  "family_name": "{{user.last_name}}",
  "picture": "{{user.image_url}}"
}
```

## Why Email is Critical

Without `email` in the token:

- ❌ Cannot link existing users during migration
- ❌ New users get placeholder emails (`{clerk_user_id}@clerk.local`)
- ❌ User-specific content queries may fail or return wrong data
- ❌ Dashboard and other user-specific features won't work correctly

With `email` in the token:

- ✅ Proper user identification and linking
- ✅ Correct user-specific content in dashboard
- ✅ Proper email addresses for all users
- ✅ Seamless user experience

## Testing

After updating your JWT template:

1. Sign out and sign back in to get a new token
2. Check browser console for "Token verified" logs
3. Verify dashboard loads user-specific data
4. Check backend logs to confirm email is present in token claims
