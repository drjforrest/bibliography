# Quick Token Test Script

## Step 1: Check Network Tab (RECOMMENDED - Easiest Method)

1. Open DevTools (F12 or Cmd+Option+I)
2. Go to **Network** tab
3. Filter by typing `/api/v1/` in the filter box
4. Refresh the page or trigger an API call
5. Look for requests that show **403** status (red)
6. Click on one of those requests
7. Go to **Headers** tab
8. Scroll down to **Request Headers**
9. Look for `Authorization: Bearer eyJ...`
   - ✅ **If present**: Copy the token and test it with Step 2
   - ❌ **If missing**: The token isn't being sent - this is the problem!

## Step 1b: Get Your Token in Browser Console (Alternative)

If you prefer to use console, open your browser console on `https://library.counterforce-hero.tech` and run:

```javascript
// Method 1: Check Network Tab (EASIEST)
// 1. Open DevTools → Network tab
// 2. Filter by "/api/v1/"
// 3. Find a failing request (403)
// 4. Click on it → Headers tab
// 5. Look for "Authorization: Bearer ..." in Request Headers
// 6. Copy the token value

// Method 2: Intercept fetch/axios to capture tokens (Browser Console)
// This will show you tokens as they're sent to your API
const originalFetch = window.fetch;
window.fetch = function (...args) {
  const [url, options] = args;
  if (url && (url.includes("/api/v1/") || url.includes("/debug/token"))) {
    console.log("🔍 API Request:", url);
    const authHeader =
      options?.headers?.Authorization ||
      options?.headers?.["authorization"] ||
      (options?.headers && typeof options.headers.get === "function"
        ? options.headers.get("Authorization")
        : null);

    if (authHeader) {
      const token = authHeader.replace("Bearer ", "");
      console.log("✅ Token found:", token.substring(0, 50) + "...");

      // Decode and show claims
      try {
        const parts = token.split(".");
        const payload = JSON.parse(atob(parts[1]));
        console.log("📋 Token claims:", {
          issuer: payload.iss,
          audience: payload.aud,
          user: payload.sub,
          email: payload.email,
          expires: new Date(payload.exp * 1000).toLocaleString(),
        });
      } catch (e) {
        console.error("❌ Error decoding token:", e);
      }
    } else {
      console.error("❌ NO AUTHORIZATION HEADER! Token not being sent.");
    }
  }
  return originalFetch.apply(this, args);
};
console.log(
  "✅ Fetch interceptor installed. Now trigger an API request to see the token."
);

// Method 3: Check localStorage/sessionStorage for Clerk data
console.log(
  "localStorage Clerk keys:",
  Object.keys(localStorage).filter(
    (k) => k.includes("clerk") || k.includes("__clerk")
  )
);
console.log(
  "sessionStorage Clerk keys:",
  Object.keys(sessionStorage).filter(
    (k) => k.includes("clerk") || k.includes("__clerk")
  )
);

// Method 4: Intercept fetch requests to see tokens being sent
const originalFetch = window.fetch;
window.fetch = function (...args) {
  const [url, options] = args;
  if (url && url.includes("/api/v1/")) {
    console.log("API Request:", url);
    console.log("Headers:", options?.headers);
    if (options?.headers?.Authorization) {
      const token = options.headers.Authorization.replace("Bearer ", "");
      console.log("Token found:", token.substring(0, 50) + "...");
      // Decode token
      try {
        const parts = token.split(".");
        const payload = JSON.parse(atob(parts[1]));
        console.log("Token claims:", {
          iss: payload.iss,
          aud: payload.aud,
          sub: payload.sub,
          exp: new Date(payload.exp * 1000),
          email: payload.email,
        });
      } catch (e) {
        console.error("Error decoding token:", e);
      }
    } else {
      console.warn("⚠️ NO AUTHORIZATION HEADER FOUND!");
    }
  }
  return originalFetch.apply(this, args);
};
console.log(
  "✅ Fetch interceptor installed. Make an API request to see the token."
);
```

## Step 2: Test Token with Debug Endpoint

Once you have the token, test it:

```bash
# Replace YOUR_TOKEN with the actual token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://library.counterforce-hero.tech/debug/token | jq
```

## Step 3: Check Network Tab

1. Open DevTools → Network tab
2. Filter by "Fetch/XHR"
3. Look for requests to `/api/v1/...`
4. Click on a failing request (403)
5. Check the "Headers" tab
6. Look for "Authorization" header
7. Copy the token value

## Step 4: Decode Token (Optional)

You can decode the JWT to see its contents:

```javascript
// In browser console
const token = "YOUR_TOKEN_HERE";
const parts = token.split(".");
const header = JSON.parse(atob(parts[0]));
const payload = JSON.parse(atob(parts[1]));

console.log("Header:", header);
console.log("Payload:", payload);
console.log("Issuer (iss):", payload.iss);
console.log("Subject (sub):", payload.sub);
console.log("Audience (aud):", payload.aud);
console.log("Expiration (exp):", new Date(payload.exp * 1000));
```

## Step 5: Verify Token Claims Match Config

Check that:

- `iss` (issuer) matches: `https://clerk.counterforce-hero.tech`
- `aud` (audience) matches your `CLERK_AUDIENCE` if set
- `exp` (expiration) is in the future
- `sub` (subject) contains a valid user ID
