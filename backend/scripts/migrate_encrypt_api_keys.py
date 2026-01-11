#!/usr/bin/env python3
"""
Migrate existing plain-text API keys to encrypted format.

This script:
1. Reads existing plain-text API keys from the database
2. Re-assigns them to trigger automatic encryption by sqlalchemy-utils
3. Updates all users with encrypted keys

Usage:
    python scripts/migrate_encrypt_api_keys.py

Prerequisites:
- ENCRYPTION_KEY must be set in .env file
- Database must be accessible
- Backup recommended before running

Safety:
- This script is idempotent (safe to run multiple times)
- If keys are already encrypted, re-running will re-encrypt (safe but unnecessary)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db import async_session_maker, User
from app.config import config


async def migrate_api_keys():
    """
    Migrate existing plain-text API keys to encrypted format.

    The encryption happens automatically when we access and re-set the values.
    SQLAlchemy-utils EncryptedType encrypts data on write.
    """
    # Check that encryption key is configured
    if not config.ENCRYPTION_KEY:
        print("❌ ERROR: ENCRYPTION_KEY not set in environment!")
        print("\nTo fix this:")
        print("1. Generate a key:")
        print('   python -c "import secrets; print(secrets.token_urlsafe(32))"')
        print("\n2. Add to .env file:")
        print("   ENCRYPTION_KEY=<your-generated-key>")
        print("\n3. Restart this script")
        return 1

    print("🔐 Database API Key Encryption Migration")
    print("=" * 50)
    print(f"Encryption key configured: ✓")
    print()

    try:
        async with async_session_maker() as session:
            # Fetch all users
            result = await session.execute(select(User))
            users = result.scalars().all()

            if not users:
                print("ℹ️  No users found in database - nothing to migrate")
                return 0

            print(f"Found {len(users)} users to process\n")

            migrated_count = 0
            for idx, user in enumerate(users, 1):
                user_updates = []

                # Check and re-encrypt each API key field
                # The re-assignment triggers encryption if not already encrypted
                if user.openrouter_api_key:
                    temp = user.openrouter_api_key
                    user.openrouter_api_key = temp
                    user_updates.append("openrouter")

                if user.openai_api_key:
                    temp = user.openai_api_key
                    user.openai_api_key = temp
                    user_updates.append("openai")

                if user.elevenlabs_api_key:
                    temp = user.elevenlabs_api_key
                    user.elevenlabs_api_key = temp
                    user_updates.append("elevenlabs")

                if user_updates:
                    migrated_count += 1
                    keys_str = ", ".join(user_updates)
                    print(f"  [{idx}/{len(users)}] User {user.email}: Encrypted {keys_str} keys")
                else:
                    print(f"  [{idx}/{len(users)}] User {user.email}: No API keys set (skipped)")

            # Commit all changes
            await session.commit()

            print()
            print("=" * 50)
            print(f"✅ Migration complete!")
            print(f"   Total users: {len(users)}")
            print(f"   Users with keys encrypted: {migrated_count}")
            print(f"   Users with no keys: {len(users) - migrated_count}")
            print()
            print("All API keys are now encrypted at rest in the database.")
            return 0

    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ ERROR during migration: {e}")
        print()
        print("Troubleshooting:")
        print("- Check database connection (DATABASE_URL in .env)")
        print("- Verify ENCRYPTION_KEY is valid")
        print("- Ensure no other processes are modifying users table")
        print("- Check logs for more details")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(migrate_api_keys())
    sys.exit(exit_code)
