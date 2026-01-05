# Database Connection Fix Script (v1)

This script helps diagnose and fix database connection issues for the HERO Evidence Library v1.

## Problem

The v1 codebase needed to connect to the production database on the mac-mini server with proper configuration.

## Solution

This script:
1. ✅ Tests database connectivity with detailed error reporting
2. ✅ Verifies all existing tables
3. ✅ Checks critical table schemas (user, scientific_papers)
4. ✅ Provides table inspector for detailed examination
5. ✅ Gives clear diagnostic output and troubleshooting steps

## Quick Start

### Step 1: Update your .env file

In your `.env`, update the DATABASE_URL:

```bash
DATABASE_URL="postgresql+asyncpg://jforrest:Forrest14$@192.168.1.69:5432/hero_evidence_library_prod"
```

**Critical Points:**
- ✅ Use `192.168.1.69` (IP address) - more reliable than hostname
- ✅ Password is `Forrest14$` - dollar sign NOT escaped
- ✅ Use `asyncpg` driver for async connections
- ✅ Database name: `hero_evidence_library_prod`

### Step 2: Ensure dependencies are installed

```bash
pip install sqlalchemy asyncpg
```

### Step 3: Run the script

```bash
# From your project root
python scripts/fix_database_connection.py
```

## What You'll See

### Successful Connection
```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║  HERO Evidence Library v1 - Database Check Script       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

============================================================
STEP 1: Testing Database Connection
============================================================
✅ Connection successful!
   Server: 192.168.1.69:5432
   Database: hero_evidence_library_prod
   PostgreSQL: PostgreSQL 17.7 (Homebrew)...
```

### Table Verification
```
============================================================
STEP 2: Verifying Existing Tables
============================================================

📋 Found 17 tables:
   - chats
   - chunks
   - devonthink_folders
   - documents
   - scientific_papers
   - user
   ... (etc)
```

### Schema Checks
```
============================================================
STEP 3: Checking Key Table Schemas
============================================================

✓ user.id type: uuid
✓ scientific_papers.id type: integer
```

### Table Inspector
```
============================================================
Table Detail Inspector
============================================================

Would you like to inspect a specific table?
Enter table name (or press Enter to skip): user

📋 Table: user
------------------------------------------------------------
Column                         Type                 Nullable  
------------------------------------------------------------
id                             uuid                 NO        
email                          character varying    NO        
clerk_user_id                  character varying    NO        
created_at                     timestamp with...    NO        
openrouter_api_key            character varying    YES       
```

## Common Issues & Solutions

### Issue 1: Connection Refused
```
❌ Connection failed: Cannot connect to host 192.168.1.69:5432
Error details: ConnectionRefusedError
```

**Solutions:**
1. Check mac-mini is on network: `ping 192.168.1.69`
2. Verify PostgreSQL is running: `telnet 192.168.1.69 5432`
3. Check PostgreSQL allows remote connections (`postgresql.conf`):
   ```
   listen_addresses = '*'
   ```
4. Check `pg_hba.conf` allows your connection:
   ```
   host    all    all    192.168.1.0/24    md5
   ```

### Issue 2: Authentication Failed
```
❌ Connection failed: password authentication failed for user "jforrest"
```

**Solution:** 
- Password must be exactly `Forrest14$` (with dollar sign)
- In connection string, do NOT escape the dollar sign
- Correct: `Forrest14$`
- Wrong: `Forrest14\$` or `Forrest14\\$`

### Issue 3: No Module Named 'asyncpg'
```
ModuleNotFoundError: No module named 'asyncpg'
```

**Solution:**
```bash
pip install asyncpg
# Or if using poetry:
poetry add asyncpg
```

### Issue 4: SSL Connection Error
```
❌ Connection failed: SSL connection has been closed unexpectedly
```

**Solution:** Add SSL mode to connection string:
```bash
DATABASE_URL="postgresql+asyncpg://jforrest:Forrest14$@192.168.1.69:5432/hero_evidence_library_prod?ssl=prefer"
```

## Using the Table Inspector

The script includes an interactive table inspector:

```bash
# Run script
python scripts/fix_database_connection.py

# When prompted, enter table name:
Enter table name (or press Enter to skip): scientific_papers

# View detailed schema:
📋 Table: scientific_papers
------------------------------------------------------------
Column                         Type                 Nullable  
------------------------------------------------------------
id                             integer              NO        
title                          text                 NO        
abstract                       text                 YES       
authors                        text array           YES       
doi                            character varying    YES       
publication_date              date                 YES       
```

## Quick Connection Test

Just want to test if connection works? Run this one-liner:

```bash
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine(
        'postgresql+asyncpg://jforrest:Forrest14\$@192.168.1.69:5432/hero_evidence_library_prod',
        echo=False
    )
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT version()'))
        print(f'✅ Connected: {result.scalar()[:60]}')
    await engine.dispose()

asyncio.run(test())
"
```

## Network Troubleshooting

### Test 1: Can you reach the server?
```bash
ping 192.168.1.69
# Expected: Reply from 192.168.1.69
```

### Test 2: Is PostgreSQL listening?
```bash
telnet 192.168.1.69 5432
# Expected: Connected to 192.168.1.69
# Press Ctrl+C to exit
```

### Test 3: DNS vs IP
```bash
# Try with hostname (may fail)
ping mac-mini

# Try with IP (should work)
ping 192.168.1.69
```

**Recommendation:** Always use IP address `192.168.1.69` in production config.

## Differences from v2

This v1 script is simplified compared to v2:
- ❌ No table creation (v1 uses different migration system)
- ❌ No v2-specific checks (podcasts, infographics tables)
- ✅ Interactive table inspector
- ✅ Better error messages and troubleshooting
- ✅ Works with v1's existing database structure

## Integration with v1

To integrate this into your workflow:

1. **Before migrations:**
   ```bash
   python scripts/fix_database_connection.py
   # Verify connection before running alembic
   ```

2. **Debugging connection issues:**
   ```bash
   # Quick check
   python scripts/fix_database_connection.py
   
   # Examine specific table
   # (enter table name when prompted)
   ```

3. **In CI/CD:**
   ```bash
   # Non-interactive check
   python scripts/fix_database_connection.py < /dev/null
   # Exit code 0 = success, non-zero = failure
   ```

## Key Learnings from v2's Experience

1. **IP > Hostname**: Use `192.168.1.69` instead of `mac-mini`
2. **Password escaping**: Do NOT escape the `$` in connection string
3. **Driver matters**: Use `asyncpg` not `psycopg2` for async
4. **Schema types**: Verify `user.id` is UUID type
5. **Test first**: Always verify connection before migrations

## Questions?

If you're still having issues:

1. ✅ Run this script for diagnostics
2. ✅ Check the error messages carefully
3. ✅ Verify network connectivity to 192.168.1.69
4. ✅ Confirm PostgreSQL is running on mac-mini
5. ✅ Check your `.env` file has the exact connection string
6. ✅ Ensure `asyncpg` is installed

The script is designed to give you detailed error information to help pinpoint the exact issue.

Good luck! 🚀

---

**Pro Tip:** Bookmark this for your team - works for any PostgreSQL connection debugging!
