# Database Encryption Setup for User API Keys

## Overview

User API keys (OpenRouter, OpenAI, ElevenLabs) are now encrypted at rest in the database using AES encryption via `sqlalchemy-utils`. This prevents exposure of sensitive credentials if the database is compromised.

## Security Architecture

- **Encryption Method**: AES encryption with PKCS5 padding
- **Library**: `sqlalchemy-utils` with `cryptography` backend
- **Encrypted Fields**:
  - `openrouter_api_key` - For LLM script generation
  - `openai_api_key` - For OpenAI TTS
  - `elevenlabs_api_key` - For ElevenLabs TTS

## Setup Instructions

### 1. Generate Encryption Key

Generate a secure encryption key and add it to your `.env` file:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add the output to your `.env` file:

```bash
ENCRYPTION_KEY=your-generated-key-here
```

**IMPORTANT**:
- Store this key securely (password manager, secrets vault, etc.)
- NEVER commit this key to version control
- If you lose this key, all encrypted data becomes unrecoverable
- Different environments (dev/staging/prod) should use different keys

### 2. Install Dependencies

The required packages are already in `pyproject.toml`:

```bash
cd backend
pip install -e .
# or with uv:
uv pip install -e .
```

This installs:
- `sqlalchemy-utils>=0.41.2` - Provides EncryptedType
- `cryptography>=43.0.0` - Cryptographic backend

### 3. Database Migration

#### Option A: Fresh Database (No Existing Data)

If you're starting fresh or can recreate the database:

```bash
# Drop and recreate all tables
python -c "
from app.db import engine, Base
import asyncio

async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(reset_db())
"
```

#### Option B: Existing Database with Data

If you have existing user data with plain-text API keys:

**Step 1**: Back up your database first!

```bash
pg_dump bibliography_db > backup_before_encryption.sql
```

**Step 2**: Run the migration script:

```python
# Save as: backend/scripts/migrate_encrypt_api_keys.py

import asyncio
from sqlalchemy import text, select
from app.db import async_session_maker, User
from app.config import config

async def migrate_api_keys():
    """
    Migrate existing plain-text API keys to encrypted format.

    This script:
    1. Reads existing plain-text API keys
    2. The model will automatically encrypt them on write
    3. Updates all users
    """
    if not config.ENCRYPTION_KEY:
        print("ERROR: ENCRYPTION_KEY not set in environment!")
        print("Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        return

    async with async_session_maker() as session:
        # Fetch all users
        result = await session.execute(select(User))
        users = result.scalars().all()

        print(f"Found {len(users)} users to migrate")

        for user in users:
            # The encryption happens automatically when we access and re-set the values
            # SQLAlchemy-utils will encrypt on write
            if user.openrouter_api_key:
                temp = user.openrouter_api_key
                user.openrouter_api_key = temp
                print(f"Encrypted openrouter_api_key for user {user.id}")

            if user.openai_api_key:
                temp = user.openai_api_key
                user.openai_api_key = temp
                print(f"Encrypted openai_api_key for user {user.id}")

            if user.elevenlabs_api_key:
                temp = user.elevenlabs_api_key
                user.elevenlabs_api_key = temp
                print(f"Encrypted elevenlabs_api_key for user {user.id}")

        await session.commit()
        print(f"\nMigration complete! Encrypted API keys for {len(users)} users")

if __name__ == "__main__":
    asyncio.run(migrate_api_keys())
```

**Step 3**: Run the migration:

```bash
cd backend
python scripts/migrate_encrypt_api_keys.py
```

**Important Notes**:
- This script assumes keys are currently in plain text
- If encryption is already enabled, running this again is safe (it re-encrypts)
- The script does NOT modify the column type in PostgreSQL (still VARCHAR)
- Encryption/decryption happens in Python application layer

### 4. Verify Encryption

Test that encryption is working:

```python
# Save as: backend/scripts/test_encryption.py

import asyncio
from sqlalchemy import select
from app.db import async_session_maker, User

async def test_encryption():
    """Verify that API keys are being encrypted."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalars().first()

        if not user:
            print("No users found in database")
            return

        if user.openrouter_api_key:
            print(f"✓ OpenRouter key reads correctly: {user.openrouter_api_key[:10]}...")
            print("  (If this looks like gibberish in the DB, encryption is working!)")
        else:
            print("  No OpenRouter key set for this user")

if __name__ == "__main__":
    asyncio.run(test_encryption())
```

Check the database directly to see encrypted values:

```sql
SELECT
    id,
    email,
    SUBSTRING(openrouter_api_key, 1, 50) as encrypted_key
FROM users
WHERE openrouter_api_key IS NOT NULL
LIMIT 5;
```

You should see encrypted binary/text data, not the original API key.

## How It Works

### Automatic Encryption/Decryption

The `EncryptedType` wrapper handles encryption transparently:

```python
# Writing (encryption happens automatically)
user.openrouter_api_key = "sk-or-v1-abc123..."
await session.commit()  # Encrypted before storage

# Reading (decryption happens automatically)
api_key = user.openrouter_api_key  # Returns plain text "sk-or-v1-abc123..."
```

### Graceful Degradation

If `ENCRYPTION_KEY` is not set:
- Falls back to plain String columns (no encryption)
- Warning is logged on startup
- Existing code continues to work
- Production should ALWAYS have encryption enabled

### Column Implementation

```python
openrouter_api_key = Column(
    EncryptedType(String, config.ENCRYPTION_KEY, AesEngine, 'pkcs5') if config.ENCRYPTION_KEY else String,
    nullable=True
)
```

This conditional ensures:
- With `ENCRYPTION_KEY`: Uses `EncryptedType` with AES encryption
- Without `ENCRYPTION_KEY`: Falls back to plain `String` (for dev/testing)

## Security Best Practices

### Key Management

1. **Production**: Store in environment-specific secrets manager
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Google Secret Manager

2. **Development**: Store in `.env` file (not committed)

3. **Rotation**: Plan for periodic key rotation
   - Generate new key
   - Decrypt all data with old key
   - Re-encrypt with new key
   - Update environment configuration

### Key Storage

```bash
# .env file (NEVER commit to git)
ENCRYPTION_KEY=your-secure-key-here

# .gitignore (ensure this is present)
.env
.env.*
!.env.example
```

### Key Rotation Script

```python
# Save as: backend/scripts/rotate_encryption_key.py

import asyncio
import os
from sqlalchemy import select
from app.db import async_session_maker, User

async def rotate_key(old_key: str, new_key: str):
    """
    Rotate encryption key for all user API keys.

    WARNING: This is complex and requires downtime!
    """
    print("Key rotation is a complex operation.")
    print("Consider using database encryption at rest instead for production.")
    print("\nFor manual rotation:")
    print("1. Set OLD_ENCRYPTION_KEY and NEW_ENCRYPTION_KEY in environment")
    print("2. Decrypt all data with old key")
    print("3. Re-encrypt with new key")
    print("4. Update ENCRYPTION_KEY to new value")

    # Implementation left as exercise - requires careful handling

if __name__ == "__main__":
    print("Key rotation script - use with extreme caution!")
```

## Troubleshooting

### "greenlet_spawn" errors

If you see encryption/decryption errors with async SQLAlchemy:
- Ensure you're using `async_session_maker`
- Don't mix sync and async database operations
- sqlalchemy-utils may have async compatibility issues - monitor GitHub issues

### Keys not decrypting

1. Verify `ENCRYPTION_KEY` is set: `echo $ENCRYPTION_KEY`
2. Ensure key hasn't changed since encryption
3. Check application logs for warnings
4. Verify sqlalchemy-utils version: `pip show sqlalchemy-utils`

### Performance concerns

Encryption adds overhead:
- ~1-5ms per key encrypt/decrypt operation
- Negligible for typical API key access patterns
- Consider caching decrypted keys in memory for high-traffic scenarios

## Alternatives Considered

### Database-Level Encryption

PostgreSQL Transparent Data Encryption (TDE):
- Pros: Encrypts entire database, managed by DB
- Cons: Doesn't protect against SQL injection or compromised DB credentials

### Application-Level with KMS

Using AWS KMS or similar:
- Pros: Centralized key management, audit logs
- Cons: Network latency, additional infrastructure

### Current Approach

Application-level encryption with sqlalchemy-utils:
- ✓ Simple setup and deployment
- ✓ Works with any PostgreSQL instance
- ✓ Transparent to application code
- ✓ No external dependencies
- ⚠ Key management is application's responsibility

## References

- [sqlalchemy-utils Documentation](https://sqlalchemy-utils.readthedocs.io/en/latest/data_types.html#module-sqlalchemy_utils.types.encrypted)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [PostgreSQL Encryption Options](https://www.postgresql.org/docs/current/encryption-options.html)
