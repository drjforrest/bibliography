# Hydration Issues - Fixes Applied

## Issues Identified

### 1. ✅ Fixed: ThemeProvider Returning Null on First Render

**Problem**: 
- `ThemeProvider` was returning `null` on server render (when `mounted === false`)
- Client would render children after mount, causing hydration mismatch
- This caused React to discard server HTML and re-render, leading to visual glitches

**Fix Applied**:
- Changed `ThemeProvider` to always render children
- Server and client both start with `'light'` theme
- Theme is updated in `useEffect` after mount, but children are always rendered
- This ensures server and client render match initially

**File**: `frontend/nextjs-app/components/ThemeProvider.tsx`

### 2. ✅ Fixed: CSS @import Order

**Problem**:
- CSS @import rules must come before all other CSS rules (except @charset and @layer)
- Build warnings showed @import rules appearing after other CSS
- This can cause styles to load incorrectly

**Fix Applied**:
- Added comment clarifying @import rules must be at the top
- Ensured @import statements are before @theme directive

**File**: `frontend/nextjs-app/app/globals.css`

### 3. ⚠️ Remaining: Font Loading Issues

**Problem**:
- Text rendering shows garbled characters ("da hboard" instead of "Dashboard")
- Fonts are loaded via:
  1. Next.js font optimization (Inter, Merriweather)
  2. CSS @import (same fonts)
  3. External link tag (Material Symbols)

**Potential Causes**:
- Fonts loading at different times on server vs client
- Font fallback not working properly
- Font variables not applied correctly

**Recommendation**:
- Consider removing duplicate font loading (either use Next.js optimization OR CSS @import, not both)
- Ensure font variables are applied correctly
- Add font-display: swap to prevent invisible text

### 4. ⚠️ Remaining: API 500 Errors

**Problem**:
- `/api/v1/papers` and `/api/v1/tags/hierarchy` returning 500 errors
- Backend fixes haven't been deployed yet

**Fix Needed**:
- Redeploy backend with updated `tags_routes.py` (using Clerk auth)

## Testing After Fixes

1. **Check for hydration warnings**:
   - Open browser console
   - Look for "Hydration failed" or "Text content does not match" warnings
   - Should be gone after ThemeProvider fix

2. **Check theme switching**:
   - Toggle dark/light mode
   - Should work without visual glitches
   - No flash of wrong theme

3. **Check font rendering**:
   - Text should render correctly on first paint
   - No garbled characters
   - Fonts should load smoothly

4. **Check API calls**:
   - After backend redeploy, API calls should succeed
   - Papers and tags should load

## Next Steps

1. **Redeploy frontend** with these fixes
2. **Redeploy backend** with Clerk auth fixes for tags routes
3. **Monitor** for any remaining hydration warnings
4. **Consider** removing duplicate font loading if issues persist

## Additional Recommendations

### Font Loading Optimization

If font issues persist, consider:

1. **Use only Next.js font optimization** (recommended):
   ```tsx
   // Remove @import from globals.css
   // Keep only Next.js font optimization in layout.tsx
   ```

2. **Add font-display: swap**:
   ```css
   @font-face {
     font-family: 'Inter';
     font-display: swap;
   }
   ```

3. **Preload critical fonts**:
   ```tsx
   <link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
   ```

### Theme Provider Alternative

If theme issues persist, consider using Next.js built-in theme support or a library like `next-themes` which handles SSR properly.

