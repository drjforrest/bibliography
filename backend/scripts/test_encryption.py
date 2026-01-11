#!/usr/bin/env python3
"""
Test script to verify API key encryption is working correctly.

This script:
1. Checks if ENCRYPTION_KEY is configured
2. Tests reading encrypted API keys
3. Verifies encryption by checking database directly
4. Provides diagnostics

Usage:
    python scripts/test_encryption.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from app.db import async_session_maker, User, engine
from app.config import config


async def test_encryption():
    """Test that API key encryption is working correctly."""
    print("🔐 API Key Encryption Test")
    print("=" * 50)

    # Check encryption key
    if not config.ENCRYPTION_KEY:
        print("❌ ENCRYPTION_KEY not set!")
        print("\nEncryption is NOT enabled. API keys are stored in plain text.")
        print("\nTo enable encryption:")
        print('1. Generate key: python -c "import secrets; print(secrets.token_urlsafe(32))"')
        print("2. Add to .env: ENCRYPTION_KEY=<your-key>")
        print("3. Run migration: python scripts/migrate_encrypt_api_keys.py")
        return 1

    print(f"✓ Encryption key configured: {config.ENCRYPTION_KEY[:10]}...{config.ENCRYPTION_KEY[-10:]}")
    print()

    try:
        async with async_session_maker() as session:
            # Find users with API keys
            result = await session.execute(
                select(User).where(
                    (User.openrouter_api_key.isnot(None)) |
                    (User.openai_api_key.isnot(None)) |
                    (User.elevenlabs_api_key.isnot(None))
                ).limit(5)
            )
            users = result.scalars().all()

            if not users:
                print("ℹ️  No users with API keys found")
                print("\nTo test encryption:")
                print("1. Add an API key to a user account through the UI")
                print("2. Run this test again")
                return 0

            print(f"Found {len(users)} user(s) with API keys\n")

            for idx, user in enumerate(users, 1):
                print(f"User {idx}: {user.email}")

                # Test reading (decryption)
                if user.openrouter_api_key:
                    key = user.openrouter_api_key
                    print(f"  ✓ OpenRouter key decrypts: {key[:15]}...{key[-5:]}")

                if user.openai_api_key:
                    key = user.openai_api_key
                    print(f"  ✓ OpenAI key decrypts: {key[:15]}...{key[-5:]}")

                if user.elevenlabs_api_key:
                    key = user.elevenlabs_api_key
                    print(f"  ✓ ElevenLabs key decrypts: {key[:15]}...{key[-5:]}")

                print()

        # Check raw database values
        print("\n" + "=" * 50)
        print("Checking database for encrypted values...")
        print()

        async with engine.begin() as conn:
            # Query raw column values
            result = await conn.execute(
                text("""
                    SELECT
                        email,
                        SUBSTRING(openrouter_api_key::text, 1, 50) as openrouter_preview,
                        SUBSTRING(openai_api_key::text, 1, 50) as openai_preview,
                        SUBSTRING(elevenlabs_api_key::text, 1, 50) as elevenlabs_preview
                    FROM users
                    WHERE
                        openrouter_api_key IS NOT NULL
                        OR openai_api_key IS NOT NULL
                        OR elevenlabs_api_key IS NOT NULL
                    LIMIT 5
                """)
            )

            rows = result.fetchall()

            if not rows:
                print("No encrypted keys found in database")
            else:
                print("Raw database values (first 50 chars):")
                for row in rows:
                    print(f"\nUser: {row[0]}")
                    if row[1]:
                        # Check if it looks encrypted (contains non-printable chars or base64-like)
                        is_encrypted = not all(32 <= ord(c) < 127 for c in str(row[1])[:20])
                        status = "🔐 ENCRYPTED" if is_encrypted else "⚠️  PLAIN TEXT"
                        print(f"  OpenRouter: {status} - {row[1]}")
                    if row[2]:
                        is_encrypted = not all(32 <= ord(c) < 127 for c in str(row[2])[:20])
                        status = "🔐 ENCRYPTED" if is_encrypted else "⚠️  PLAIN TEXT"
                        print(f"  OpenAI: {status} - {row[2]}")
                    if row[3]:
                        is_encrypted = not all(32 <= ord(c) < 127 for c in str(row[3])[:20])
                        status = "🔐 ENCRYPTED" if is_encrypted else "⚠️  PLAIN TEXT"
                        print(f"  ElevenLabs: {status} - {row[3]}")

        print("\n" + "=" * 50)
        print("✅ Encryption test complete!")
        print("\nWhat this means:")
        print("- '🔐 ENCRYPTED' = Keys stored encrypted in database (GOOD)")
        print("- '⚠️  PLAIN TEXT' = Keys stored unencrypted (RUN MIGRATION)")
        print("\nIf you see plain text, run: python scripts/migrate_encrypt_api_keys.py")
        return 0

    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ ERROR during test: {e}")
        print("\nTroubleshooting:")
        print("- Check database connection (DATABASE_URL in .env)")
        print("- Verify sqlalchemy-utils is installed: pip show sqlalchemy-utils")
        print("- Check that User model has EncryptedType columns")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_encryption())
    sys.exit(exit_code)
