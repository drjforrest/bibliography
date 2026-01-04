# Fix: Missing clerk_user_id Column

## Issue
Backend is returning 401 errors with this error in logs:
```
AttributeError: type object 'User' has no attribute 'clerk_user_id'
```

## Root Cause
The User model was missing the `clerk_user_id` column definition, and the database table also needs this column added.

## Fix Applied
1. ✅ Added `clerk_user_id` column to User model in `backend/app/db.py` (both AUTH_TYPE branches)

## Next Steps - Run Database Migration

The database table also needs the column. Run the migration script on production:

```bash
# SSH to mac-mini
ssh mac-mini
cd ~/production/hero-evidence-library/backend

# Activate virtual environment
source venv/bin/activate

# Run the migration script
python scripts/add_clerk_user_id_migration.py
```

This will:
- Check if the column exists
- Add `clerk_user_id VARCHAR(255) UNIQUE` column if missing
- Create an index for faster lookups

## After Migration

1. **Restart the backend**:
   ```bash
   # On mac-mini
   pkill -f "uvicorn.*8400"
   cd ~/production/hero-evidence-library/backend
   source venv/bin/activate
   nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8400 > ../hero_evidence_library_backend.log 2>&1 &
   ```

2. **Verify the fix**:
   - Test API calls from the frontend
   - Check backend logs - should no longer see "AttributeError: type object 'User' has no attribute 'clerk_user_id'"
   - API calls should return 200 instead of 401

## Verification

After migration and restart, check logs:
```bash
tail -f ~/production/hero-evidence-library/hero_evidence_library_backend.log
```

You should see:
- "Token verified successfully for user: ..."
- No more AttributeError
- Successful user creation/retrieval

