# Clerk Webhook Configuration Verification

## ✅ Current Setup

### Webhook Endpoint URL

- **Full URL**: `https://api.counterforce-hero.tech/webhooks/clerk`
- **Route Path**: `/webhooks/clerk` (defined in `backend/app/routes/clerk_routes.py`)
- **HTTP Method**: `POST`

### Environment Variables

- ✅ `CLERK_WEBHOOK_SECRET` - Added to `.env.production`
- ✅ Secret obtained from Clerk Dashboard → Webhooks → [Your Endpoint] → Signing Secret

## Verification Checklist

### In Clerk Dashboard

- [ ] Webhook endpoint URL is set to: `https://api.counterforce-hero.tech/webhooks/clerk`
- [ ] Webhook events are subscribed:
  - [ ] `user.created`
  - [ ] `user.updated`
  - [ ] `user.deleted`
- [ ] Webhook is **enabled** (not paused/disabled)

### In Your Backend

- [ ] `CLERK_WEBHOOK_SECRET` is set in `.env.production`
- [ ] Secret value matches the one shown in Clerk Dashboard
- [ ] Backend server is running and accessible at `https://api.counterforce-hero.tech`

## Testing the Webhook

### Option 1: Test Endpoint

```bash
curl https://api.counterforce-hero.tech/webhooks/clerk/test
```

Expected response:

```json
{ "message": "Clerk webhook endpoint is active" }
```

### Option 2: Trigger a Test Event

1. In Clerk Dashboard, go to your webhook endpoint
2. Click "Send test event" or "Test webhook"
3. Select event type (e.g., `user.created`)
4. Check backend logs for webhook processing

### Option 3: Create a Test User

1. Sign up a new user through your frontend
2. Check backend logs for `user.created` webhook event
3. Verify user was created in your database

## Troubleshooting

### Webhook Not Receiving Events

1. **Check URL**: Verify the webhook URL in Clerk Dashboard matches exactly:

   ```
   https://api.counterforce-hero.tech/webhooks/clerk
   ```

   (Note: No `/api/v1` prefix - the route is directly at `/webhooks/clerk`)

2. **Check Secret**: Verify `CLERK_WEBHOOK_SECRET` in `.env.production` matches Clerk Dashboard

3. **Check Backend Logs**: Look for webhook-related errors:

   ```bash
   # Check backend logs
   tail -f backend/logs/backend.log | grep -i webhook
   ```

4. **Check Network**: Ensure `https://api.counterforce-hero.tech` is accessible from Clerk's servers

### "Webhook verification failed"

- Secret mismatch: Verify `CLERK_WEBHOOK_SECRET` matches Clerk Dashboard
- No quotes: Ensure secret has no quotes or extra spaces in `.env.production`
- Restart server: Restart backend after adding/updating the secret

### "Missing required webhook header"

- Clerk sends webhooks with Svix headers
- This error means the request isn't coming from Clerk
- Verify the webhook URL is correct in Clerk Dashboard

## Route Registration

The webhook route is registered in `backend/app/app.py`:

```python
app.include_router(clerk_router, tags=["clerk"])
```

This means the route is at `/webhooks/clerk` (no prefix), so the full URL is:

```
https://api.counterforce-hero.tech/webhooks/clerk
```

## Related Files

- **Route Handler**: `backend/app/routes/clerk_routes.py`
- **Service**: `backend/app/services/clerk_service.py`
- **Config**: `backend/app/config/__init__.py` (line 160)
- **Setup Guide**: `docs/CLERK_WEBHOOK_SETUP.md`
