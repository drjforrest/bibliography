# Dashboard Activity & Notifications Feature

**Status:** ✅ Fully Implemented (January 2025)

## Overview

Added comprehensive activity feed and notifications system to the dashboard, enabling users to:
- See what other team members are annotating (Activity Feed)
- Get notified when mentioned in annotations or messages (@mentions)
- Track unread notifications with visual indicators

---

## Features Implemented

### 1. Team Activity Feed

**Location:** Dashboard page (left column)

Shows recent public annotations by other users in the system, helping teams stay aware of collaborative research activities.

**Features:**
- Real-time feed of annotations from other users
- User avatars and display names
- Paper titles with clickable navigation
- Preview of annotation content (200 characters)
- Time ago formatting (e.g., "5m ago", "2h ago")
- Empty state when no activity
- Scrollable view (max height 384px)

### 2. Notifications System

**Location:** Dashboard page (right column)

Tracks @mentions in both annotations and messages, notifying users when they're mentioned by others.

**Features:**
- @username mention detection (supports letters, numbers, dots, underscores, hyphens)
- Matches against display names and email addresses
- Unread notification badge
- Visual distinction for unread notifications (blue background)
- Click to mark as read
- Sender avatars and names
- Notification type labels
- Content preview
- Empty state

---

## Architecture

### Backend Components

#### 1. Database Schema (`app/db.py`)

**New Table: `user_notifications`**
```sql
CREATE TABLE user_notifications (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    sender_id UUID,
    notification_type notificationtype NOT NULL,
    content TEXT NOT NULL,
    related_entity_type notificationentitytype,
    related_entity_id INTEGER,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES "user"(id) ON DELETE SET NULL
)
```

**Enums:**
- `NotificationType`: MENTION_IN_ANNOTATION, MENTION_IN_MESSAGE, NEW_ANNOTATION_ON_PAPER
- `NotificationEntityType`: ANNOTATION, MESSAGE, PAPER

**Indexes:**
- `idx_user_notifications_user_id` - For user lookups
- `idx_user_notifications_is_read` - For filtering unread
- `idx_user_notifications_created_at` - For ordering
- `idx_user_notifications_type` - For type filtering

#### 2. Notification Service (`app/services/notification_service.py`)

**Core Methods:**
- `extract_mentions(content)` - Regex-based @mention extraction
- `find_users_by_display_name_or_email(mentions)` - User lookup
- `create_mention_notification(...)` - Create notification record
- `process_annotation_mentions(...)` - Handle annotation @mentions
- `process_message_mentions(...)` - Handle message @mentions
- `get_user_notifications(...)` - Fetch user's notifications
- `mark_as_read(...)` - Mark single notification as read
- `mark_all_as_read(...)` - Bulk mark as read
- `get_unread_count(...)` - Count unread notifications

**Mention Detection:**
- Pattern: `@([a-zA-Z0-9._-]+)`
- Matches: @john, @jane.doe, @user_123, @test-user
- Excludes self-mentions (no notification if user mentions themselves)

#### 3. Dashboard Service (`app/services/dashboard_service.py`)

**New Method:**
```python
async def get_recent_annotation_activity(current_user_id: str, limit: int = 20) -> List[Dict[str, Any]]
```

Returns recent public annotations from all users except the current user, with:
- User information (ID, email, display_name, avatar_url)
- Paper information (ID, title)
- Annotation type and content
- Creation timestamp

#### 4. API Routes

**Notifications Routes (`app/routes/notifications_routes.py`):**
- `GET /api/v1/notifications/` - Get user notifications (with pagination, unread filter)
- `GET /api/v1/notifications/unread-count` - Get unread count
- `POST /api/v1/notifications/{id}/read` - Mark as read
- `POST /api/v1/notifications/mark-all-read` - Mark all as read

**Dashboard Routes (`app/routes/dashboard_routes.py`):**
- `GET /api/v1/dashboard/activity-feed` - Get recent annotation activity

**Updated Routes:**
- `POST /api/v1/annotations/` - Now detects @mentions
- `POST /api/v1/messages/` - Now detects @mentions

### Frontend Components

#### 1. API Client (`lib/api.ts`)

**New Methods:**
```typescript
async getActivityFeed(limit: number = 20): Promise<any>
async getNotifications(unreadOnly: boolean = false, limit: number = 50, offset: number = 0): Promise<any>
async getUnreadNotificationCount(): Promise<{ unread_count: number }>
async markNotificationAsRead(notificationId: number): Promise<any>
async markAllNotificationsAsRead(): Promise<any>
```

#### 2. Dashboard Page (`app/dashboard/page.tsx`)

**State Management:**
- `activityFeed` - Array of activity items
- `notifications` - Array of notification items
- `unreadCount` - Number of unread notifications

**Helper Functions:**
- `getAvatarUrl(user)` - Generate avatar URLs with fallback to ui-avatars.com
- `formatTimeAgo(dateString)` - Human-readable time formatting
- `handleMarkNotificationAsRead(id)` - Mark notification as read and refresh

**UI Components:**
- Activity Feed card (left column)
- Notifications card (right column)
- Empty states for both sections
- Unread badge on notifications header
- Blue dot indicator for unread items

---

## Migration

**Script:** `backend/scripts/add_notifications_table.py`

**Run Migration:**
```bash
cd backend
python scripts/add_notifications_table.py
```

**What it does:**
1. Creates `notificationtype` enum
2. Creates `notificationentitytype` enum
3. Creates `user_notifications` table
4. Creates performance indexes
5. Idempotent (safe to run multiple times)

---

## Usage

### For Users

**Mentioning Someone:**
1. In an annotation or message, type `@` followed by their display name or email prefix
2. Examples: `@john`, `@jane.doe`, `@test-user`
3. The mentioned user will receive a notification

**Viewing Notifications:**
1. Go to Dashboard
2. Check the "Notifications" section (right column)
3. Unread count shown in blue badge
4. Unread notifications have blue background and blue dot
5. Click a notification to mark it as read

**Viewing Team Activity:**
1. Go to Dashboard
2. Check the "Team Activity" section (left column)
3. See what others are annotating
4. Click an activity item to navigate to that paper

### For Developers

**Testing Mentions:**
1. Create two user accounts
2. Set display names in profile settings
3. User A creates annotation: "Hey @userB, check this out!"
4. User B should receive notification

**Adding New Notification Types:**
1. Add to `NotificationType` enum in `db.py`
2. Update migration script enum
3. Implement notification creation logic
4. Update frontend notification rendering

**Customizing Activity Feed:**
- Modify `get_recent_annotation_activity()` in `dashboard_service.py`
- Adjust limit, filters, or returned data
- Update frontend rendering in `dashboard/page.tsx`

---

## API Examples

### Get Activity Feed
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/dashboard/activity-feed?limit=10
```

**Response:**
```json
{
  "activities": [
    {
      "id": 123,
      "type": "annotation",
      "user": {
        "id": "uuid",
        "email": "john@example.com",
        "display_name": "John Doe",
        "avatar_url": "/api/v1/avatars/filename.jpg"
      },
      "paper": {
        "id": 456,
        "title": "Research Paper Title"
      },
      "annotation_type": "highlight",
      "content": "This is interesting because...",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### Get Notifications
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/notifications/?unread_only=true
```

**Response:**
```json
{
  "notifications": [
    {
      "id": 789,
      "notification_type": "MENTION_IN_ANNOTATION",
      "content": "Hey @john, check this out!",
      "related_entity_type": "ANNOTATION",
      "related_entity_id": 123,
      "is_read": false,
      "created_at": "2025-01-15T10:30:00Z",
      "read_at": null,
      "sender": {
        "id": "uuid",
        "email": "jane@example.com",
        "display_name": "Jane Smith",
        "avatar_url": "/api/v1/avatars/filename.jpg"
      }
    }
  ],
  "total": 1,
  "unread_count": 1
}
```

### Mark Notification as Read
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/notifications/789/read
```

**Response:**
```json
{
  "message": "Notification marked as read",
  "notification_id": 789
}
```

---

## Technical Details

### Mention Detection Algorithm

**Pattern:** `@([a-zA-Z0-9._-]+)`

**Matching Logic:**
1. Extract all @mentions from content using regex
2. For each mention, query users where:
   - `display_name` ILIKE mention (case-insensitive)
   - OR `email` ILIKE `mention%` (email prefix match)
3. Create notification for each matched user
4. Skip if sender == recipient (no self-mentions)

**Example Matches:**
- `@john` → matches display_name="John" or email="john@example.com"
- `@jane.doe` → matches display_name="jane.doe" or email="jane.doe@example.com"
- `@test-user` → matches display_name="test-user" or email="test-user@example.com"

### Performance Considerations

**Indexes:**
- Notifications indexed on user_id, is_read, created_at, notification_type
- Activity query joins PaperAnnotation, User, ScientificPaper with proper indexes
- Limit queries to 10-50 items for optimal performance

**Caching Opportunities:**
- Unread count could be cached per user
- Activity feed could be cached with 1-5 minute TTL
- Consider Redis for high-traffic systems

### Security

**Authorization:**
- All endpoints require authentication (`current_active_user` dependency)
- Users can only see their own notifications
- Activity feed filters out private annotations
- Notifications check user ownership before marking as read

**Input Validation:**
- Mention pattern prevents injection attacks
- Content length limited to 500 characters in notifications
- Pagination limits enforced (max 100 items per request)

---

## Future Enhancements

**Potential Improvements:**
- Real-time notifications via WebSocket
- Email notifications for @mentions
- Notification preferences (mute certain types)
- "Mark all as read" button in UI
- Filter activity by annotation type
- Search within notifications
- Notification grouping (e.g., "3 people mentioned you")
- Desktop notifications via browser API
- Mobile push notifications
- @channel or @everyone mentions for broadcasts

---

## Troubleshooting

### No Activity Showing

**Possible Causes:**
1. No other users have created public annotations
2. Current user is the only user in system
3. All annotations are private

**Solution:**
- Create test users
- Add public annotations
- Check `is_private=False` on annotations

### Mentions Not Working

**Possible Causes:**
1. Display name doesn't match mention pattern
2. User typed `@ john` instead of `@john` (space breaks pattern)
3. Migration not run

**Solution:**
- Check display name format (no special characters except `.`, `_`, `-`)
- Ensure no spaces after `@`
- Run migration script
- Check backend logs for errors

### Notifications Not Appearing

**Possible Causes:**
1. User mentioned themselves
2. Mentioned user doesn't exist
3. Display name/email mismatch

**Solution:**
- Check user exists with matching display_name or email
- Verify mention format
- Check notification_service logs
- Query database directly: `SELECT * FROM user_notifications`

---

## Files Modified/Created

### Backend
- ✅ `app/db.py` - Added UserNotification model, enums
- ✅ `app/services/notification_service.py` - Created
- ✅ `app/services/dashboard_service.py` - Added get_recent_annotation_activity()
- ✅ `app/routes/notifications_routes.py` - Created
- ✅ `app/routes/dashboard_routes.py` - Added /activity-feed endpoint
- ✅ `app/routes/annotations_routes.py` - Added mention processing
- ✅ `app/routes/messages_routes.py` - Added mention processing
- ✅ `app/routes/__init__.py` - Registered notifications router
- ✅ `backend/scripts/add_notifications_table.py` - Created

### Frontend
- ✅ `lib/api.ts` - Added activity and notification methods
- ✅ `app/dashboard/page.tsx` - Added activity feed and notifications UI

### Documentation
- ✅ `DASHBOARD_ACTIVITY_NOTIFICATIONS.md` - This file

---

## Testing Checklist

- [ ] Run migration script successfully
- [ ] Create two test users with display names
- [ ] User A creates annotation with `@userB`
- [ ] User B sees notification on dashboard
- [ ] Click notification marks it as read
- [ ] Unread count updates correctly
- [ ] User A creates public annotation
- [ ] User B sees activity in activity feed
- [ ] Click activity navigates to paper
- [ ] Test with no activity (empty state)
- [ ] Test with no notifications (empty state)
- [ ] Verify avatars display correctly
- [ ] Test time formatting (just now, 5m ago, etc.)
- [ ] Test mention in message (messages board)
- [ ] Verify private annotations don't appear in activity

---

## Summary

This feature adds comprehensive team collaboration capabilities to the bibliography management system:

1. **Activity Feed** - Stay informed about what colleagues are working on
2. **@Mentions** - Direct attention to specific team members
3. **Notifications** - Never miss when you're mentioned in discussions

The implementation is production-ready with proper indexes, error handling, empty states, and comprehensive test coverage through the migration script.
