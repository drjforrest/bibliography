# User Profile Feature Documentation

## Overview

The user profile feature allows users to customize their profile with a display name, bio, and avatar. This profile information is displayed throughout the application, including in messaging and annotation features, making it easier to identify user contributions.

## Features

### 1. Profile Settings Page (`/profile`)

A dedicated profile settings page where users can:
- **Upload Avatar**: Upload a custom avatar image (JPG, PNG, GIF, or WebP)
- **Display Name**: Set a custom display name (shown instead of email)
- **Bio**: Add a short biography
- **OpenRouter API Key**: Manage your OpenRouter API key for access to 100+ AI models (moved from sidebar)

### 2. Avatar Integration

User avatars are displayed in:
- **Message Board**: Shows user avatar next to each message and reply
- **Annotations**: Shows user avatar next to paper annotations
- **Sidebar**: User avatar in the navigation (if set)

### 3. Display Name

Users can set a custom display name that appears instead of their email address throughout the app.

## Database Schema Changes

Added new fields to the `user` table and migrated from separate API keys to OpenRouter:

```sql
-- New profile fields
ALTER TABLE "user" ADD COLUMN display_name VARCHAR(100);
ALTER TABLE "user" ADD COLUMN bio TEXT;
ALTER TABLE "user" ADD COLUMN avatar_url VARCHAR(500);

-- OpenRouter API key (replaces openai_api_key and anthropic_api_key)
ALTER TABLE "user" ADD COLUMN openrouter_api_key VARCHAR;

-- Remove old API key columns (handled automatically by migration script)
ALTER TABLE "user" DROP COLUMN openai_api_key;
ALTER TABLE "user" DROP COLUMN anthropic_api_key;
```

## Backend API Endpoints

### Profile Management

#### Get User Profile
```
GET /api/v1/profile
```

Returns the current user's profile information including:
- User ID and email
- Display name and bio
- Avatar URL
- OpenRouter API key status (whether key is set)

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "bio": "Researcher and academic",
  "avatar_url": "/avatars/uuid.jpg",
  "openrouter_api_key_set": true
}
```

#### Update User Profile
```
PUT /api/v1/profile
```

**Request Body:**
```json
{
  "display_name": "John Doe",
  "bio": "Researcher and academic"
}
```

#### Upload Avatar
```
POST /api/v1/profile/avatar
```

Upload a new avatar image (multipart/form-data).

**Supported formats:** JPG, PNG, GIF, WebP
**Max size:** 5MB (recommended)

**Response:**
```json
{
  "avatar_url": "/avatars/uuid.jpg",
  "message": "Avatar uploaded successfully"
}
```

#### Delete Avatar
```
DELETE /api/v1/profile/avatar
```

Removes the user's avatar and deletes the file.

#### Get Avatar
```
GET /api/v1/avatars/{filename}
```

Serves the avatar file.

### OpenRouter API Key Management

#### Get API Key Status
```
GET /api/v1/api-keys
```

Returns whether the user has set their OpenRouter API key.

**Response:**
```json
{
  "openrouter_api_key_set": true
}
```

#### Update API Key
```
PUT /api/v1/api-keys
```

**Request Body:**
```json
{
  "openrouter_api_key": "sk-or-v1-..."
}
```

## Frontend Components

### Profile Page
- **Location**: `/frontend/nextjs-app/app/profile/page.tsx`
- **Features**:
  - Avatar upload with preview
  - Display name and bio editing
  - API key management (consolidated)
  - Real-time validation and error handling

### Updated Components

#### MessageCard
- **Location**: `/frontend/nextjs-app/components/messages/MessageCard.tsx`
- **Changes**: Now displays user avatar and display name instead of email

#### AnnotationCard
- **Location**: `/frontend/nextjs-app/components/annotations/AnnotationCard.tsx`
- **Changes**: Now displays user avatar and display name

#### Sidebar
- **Location**: `/frontend/nextjs-app/components/layout/Sidebar.tsx`
- **Changes**:
  - Removed standalone API Key Settings
  - Added "Profile Settings" option in user menu
  - Links to `/profile` page

## File Storage

Avatars are stored in the file system (not database) at:
```
backend/data/avatars/{user_id}.{ext}
```

**Benefits:**
- Better performance
- Easier file management
- Reduces database size
- Simple backup/restore

## Migration Steps

### 1. Run Database Migration

```bash
cd backend
python scripts/add_user_profile_fields.py
```

This adds the new columns to the `user` table.

### 2. Create Avatar Directory

```bash
mkdir -p backend/data/avatars
```

### 3. Restart Backend Server

```bash
cd backend
python main.py --reload
```

### 4. Restart Frontend

```bash
cd frontend/nextjs-app
npm run dev
```

## Usage Guide

### For Users

1. **Access Profile Settings**
   - Click on your user icon/email in the sidebar
   - Select "Profile Settings" from the dropdown menu

2. **Upload Avatar**
   - Click "Choose Image" button
   - Select an image file (JPG, PNG, GIF, WebP)
   - Click "Save Changes" to upload

3. **Set Display Name**
   - Enter your preferred name in the "Display Name" field
   - This will be shown instead of your email address

4. **Add Bio**
   - Write a short biography in the "Bio" field
   - This is visible to other users (future feature)

5. **Manage API Keys**
   - Enter your OpenAI or Anthropic API keys
   - These enable AI features using your own accounts
   - Keys are stored securely and never exposed

### For Developers

#### Accessing User Profile Data

User profile data is included in API responses for messages and annotations:

```typescript
// Message user data
interface Message {
  user: {
    id: string;
    email: string;
    display_name?: string;
    avatar_url?: string;
  };
}

// Annotation user data
interface Annotation {
  user?: {
    display_name?: string;
    avatar_url?: string;
  };
}
```

#### Displaying Avatars

Use the helper function pattern:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const getAvatarUrl = (user) => {
  if (user.avatar_url) {
    return `${API_URL}${user.avatar_url}`;
  }
  const name = user.display_name || user.email;
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}`;
};
```

This provides a fallback to generated avatars when no custom avatar is set.

## Security Considerations

1. **File Type Validation**: Only image files are accepted
2. **File Storage**: Avatars are stored outside the web root
3. **Authentication Required**: All profile endpoints require authentication
4. **User Isolation**: Users can only access/modify their own profile
5. **API Keys**: Stored securely, never exposed in responses
6. **OpenRouter Integration**: User keys are separate from system RAG keys in `.env`

## OpenRouter Integration

### Why OpenRouter?

OpenRouter provides a unified API for accessing 100+ AI models from multiple providers:

- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5
- **Anthropic**: Claude 3 Opus, Sonnet, Haiku
- **Google**: Gemini Pro, Gemini Ultra
- **Meta**: Llama 3, Llama 2
- **Mistral**: Mixtral, Mistral Large
- **And many more**: Including open-source models

### How It Works

1. **System RAG**: Uses LiteLLM with keys from `.env` file (system-level)
2. **User Chat**: Uses OpenRouter with user-provided keys (user-level)
3. **Model Selection**: Users can choose from any model available on OpenRouter
4. **Unified Billing**: One API key for all models with transparent pricing

### Getting Started

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Add credits to your account
3. Copy your API key (starts with `sk-or-v1-`)
4. Add it to your profile in the app
5. Select your preferred model when chatting

## Future Enhancements

Potential improvements:
- Image resizing/compression on upload
- Avatar cropping interface
- Profile visibility settings (public/private)
- User profile pages (view other users' profiles)
- Profile completion progress indicator
- Social media links
- Two-factor authentication
- Model selector UI for OpenRouter models
- Usage tracking and cost monitoring

## Troubleshooting

### Avatar Not Displaying

1. Check that the `data/avatars` directory exists
2. Verify file permissions on the avatars directory
3. Check browser console for 404 errors
4. Ensure `NEXT_PUBLIC_API_URL` is set correctly

### Profile Updates Not Saving

1. Check authentication token is valid
2. Verify backend API is running
3. Check browser console for API errors
4. Ensure database migration was run successfully

### Display Name Not Showing

1. Refresh the page
2. Check that display_name field exists in database
3. Verify API response includes display_name
4. Check component is using display_name || email pattern

## Technical Details

### Backend Stack
- **FastAPI**: Web framework
- **SQLAlchemy**: ORM
- **PostgreSQL**: Database
- **Pydantic**: Data validation

### Frontend Stack
- **Next.js 14**: React framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

### File Structure
```
backend/
  ├── app/
  │   ├── db.py                    # Updated User model
  │   ├── routes/
  │   │   ├── user_routes.py       # Profile endpoints
  │   │   └── messages_routes.py   # Updated with avatar support
  │   └── schemas/
  │       └── messages.py          # Updated UserInfo schema
  ├── data/
  │   └── avatars/                 # Avatar storage
  └── scripts/
      └── add_user_profile_fields.py  # Migration script

frontend/nextjs-app/
  ├── app/
  │   └── profile/
  │       └── page.tsx             # Profile settings page
  ├── components/
  │   ├── layout/
  │   │   └── Sidebar.tsx          # Updated navigation
  │   ├── messages/
  │   │   └── MessageCard.tsx      # Updated with avatars
  │   └── annotations/
  │       └── AnnotationCard.tsx   # Updated with avatars
  └── types/
      └── index.ts                 # Updated type definitions
```

## Support

For issues or questions:
1. Check this documentation
2. Review the troubleshooting section
3. Check browser console for errors
4. Review backend logs
5. Verify database schema is up to date
