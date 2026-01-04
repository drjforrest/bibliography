# How to Get Clerk Webhook Signing Secret

The `CLERK_WEBHOOK_SECRET` is **not** included in Clerk's environment variable export. You need to get it separately from the Clerk Dashboard after creating a webhook endpoint.

## Step-by-Step Instructions

### Step 1: Access Clerk Dashboard

1. Go to [https://dashboard.clerk.com](https://dashboard.clerk.com)
2. Sign in to your Clerk account
3. Select your application (e.g., "counterforce-hero.tech")

### Step 2: Navigate to Webhooks

1. In the left sidebar, click on **"Webhooks"**
2. You'll see a list of webhook endpoints (or an empty list if you haven't created any)

### Step 3: Create or Select a Webhook Endpoint

#### Option A: Create a New Webhook

1. Click **"Add Endpoint"** or **"Create Endpoint"**
2. Enter your webhook URL:
   - **Production**: `https://your-backend-domain.com/api/v1/webhooks/clerk`
   - **Local Development**: Use ngrok URL like `https://abc123.ngrok.io/api/v1/webhooks/clerk`
3. Select the events you want to subscribe to:
   - ✅ `user.created` - When a new user signs up
   - ✅ `user.updated` - When user info changes
   - ✅ `user.deleted` - When a user is deleted
4. Click **"Create"** or **"Save"**

#### Option B: Use Existing Webhook

If you already have a webhook endpoint, click on it to view details.

### Step 4: Get the Signing Secret

1. After creating/selecting the webhook endpoint, you'll see the webhook details page
2. Look for a section labeled **"Signing Secret"** or **"Secret"**
3. The secret will start with `whsec_` (e.g., `whsec_abc123...`)
4. Click **"Copy"** or **"Reveal"** to see the full secret

### Step 5: Add to Your .env File

Add the secret to your `.env.production` file:

```bash
CLERK_WEBHOOK_SECRET=whsec_your_actual_secret_here
```

**Important**: 
- Keep this secret secure and never commit it to version control
- Each webhook endpoint has its own unique signing secret
- If you create a new webhook endpoint, you'll get a new secret

## Visual Guide

```
Clerk Dashboard
├── Webhooks (left sidebar)
    ├── [Your Webhook Endpoint]
        ├── Endpoint URL: https://your-backend.com/api/v1/webhooks/clerk
        ├── Events: user.created, user.updated, user.deleted
        └── Signing Secret: whsec_... ← COPY THIS
```

## Troubleshooting

### "Signing Secret not found"

- Make sure you've created a webhook endpoint first
- The secret is only shown after creating the endpoint
- Check that you're looking at the correct webhook endpoint

### "Webhook verification failed"

- Verify the secret in your `.env` matches the one in Clerk Dashboard
- Make sure there are no extra spaces or quotes around the secret
- Restart your backend server after adding the secret

### "Multiple webhook endpoints"

- Each endpoint has its own signing secret
- Use the secret from the endpoint that matches your backend URL
- You can have different secrets for development and production

## Security Notes

⚠️ **Important Security Practices**:

1. **Never commit** `CLERK_WEBHOOK_SECRET` to git
2. **Never share** the secret publicly
3. **Rotate** the secret if it's ever exposed
4. **Use different secrets** for development and production environments

## Quick Reference

- **Variable Name**: `CLERK_WEBHOOK_SECRET`
- **Format**: Starts with `whsec_`
- **Location**: Clerk Dashboard → Webhooks → [Your Endpoint] → Signing Secret
- **Required For**: Webhook signature verification in `backend/app/routes/clerk_routes.py`

## Related Documentation

- [Clerk Webhooks Documentation](https://clerk.com/docs/integrations/webhooks)
- [Webhook Route Implementation](../backend/app/routes/clerk_routes.py)
- [Environment Variables Guide](./CLERK_ENV_VERIFICATION.md)

