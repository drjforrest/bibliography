#!/usr/bin/env python3
"""
Simple script to get user ID (UUID) from the database.
Avoids importing heavy dependencies like rerankers/torch.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file if it exists
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Set required CLERK env vars to dummy values to avoid config validation errors
# These are only needed for the import, not for the actual query
if not os.getenv("CLERK_ISSUER") and not os.getenv("CLERK_FRONTEND_API_URL"):
    os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
if not os.getenv("CLERK_JWKS_URL"):
    os.environ["CLERK_JWKS_URL"] = (
        "https://dummy.clerk.accounts.dev/.well-known/jwks.json"
    )

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

# Get DATABASE_URL directly from environment to avoid importing config
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set")
    print(f"   Checked .env file at: {env_path}")
    print("   Set it in your .env file or export it:")
    print("   export DATABASE_URL='postgresql+asyncpg://user:pass@localhost/dbname'")
    sys.exit(1)


async def get_users():
    """Get all users from database using raw SQL to avoid config imports."""
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            # Query directly using raw SQL to avoid importing models/config
            # Only query columns that definitely exist
            result = await conn.execute(
                text("""
                SELECT id, email 
                FROM "user" 
                ORDER BY email
            """)
            )
            rows = result.fetchall()

            if not rows:
                print("❌ No users found in database")
                return

            print("=" * 70)
            print("👤 Users in Database")
            print("=" * 70)
            for row in rows:
                user_id, email = row
                print(f"\nEmail: {email}")
                print(f"ID (UUID): {user_id}")
            print("\n" + "=" * 70)
            print("\n💡 Use the ID (UUID) value in your import commands")
            print("   Example:")
            if rows:
                print(f"   --user-id {rows[0][0]}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(get_users())
