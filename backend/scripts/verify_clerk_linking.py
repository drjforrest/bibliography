"""
Quick script to verify Clerk user linking in the database.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path so we can import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import engine
from sqlalchemy import text


async def verify_clerk_linking():
    """Check if users are linked to Clerk accounts."""
    async with engine.begin() as conn:
        # Get all users with their clerk_user_id status
        result = await conn.execute(
            text("""
            SELECT id, email, clerk_user_id, is_active
            FROM "user"
            ORDER BY created_at
        """)
        )

        users = result.fetchall()

        print(f"\n{'=' * 60}")
        print("User Linking Status")
        print(f"{'=' * 60}\n")

        if not users:
            print("No users found in database.")
            return

        linked_count = 0
        unlinked_count = 0

        for user_id, email, clerk_user_id, is_active in users:
            status = "✓ LINKED" if clerk_user_id else "✗ NOT LINKED"
            print(f"User ID: {user_id}")
            print(f"  Email: {email}")
            print(f"  Clerk User ID: {clerk_user_id or '(not set)'}")
            print(f"  Status: {status}")
            print(f"  Active: {is_active}")
            print()

            if clerk_user_id:
                linked_count += 1
            else:
                unlinked_count += 1

        print(f"{'=' * 60}")
        print(f"Summary: {linked_count} linked, {unlinked_count} unlinked")
        print(f"{'=' * 60}\n")


async def main():
    """Run the verification."""
    try:
        await verify_clerk_linking()
    except Exception as e:
        print(f"\n✗ Verification failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
