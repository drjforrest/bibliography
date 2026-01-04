"""
Script to manually link an existing user to their Clerk user ID.

Usage:
    python scripts/link_user_to_clerk.py --email james.forrest@ubc.ca --clerk-user-id user_37ASOOzMqIfdwGNbxiTqI6o9wnR
"""

import argparse
import asyncio

from app.db import User, engine
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


async def link_user_to_clerk(email: str, clerk_user_id: str):
    """Link an existing user account to their Clerk user ID."""
    async with AsyncSession(engine) as session:
        try:
            # Find user by email
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                print(f"❌ User with email {email} not found")
                return False

            # Check if already linked
            if user.clerk_user_id == clerk_user_id:
                print(
                    f"✅ User {email} is already linked to Clerk user {clerk_user_id}"
                )
                return True

            if user.clerk_user_id:
                print(
                    f"⚠️  User {email} is already linked to a different Clerk user: {user.clerk_user_id}"
                )
                response = input(
                    f"Do you want to update it to {clerk_user_id}? (yes/no): "
                )
                if response.lower() != "yes":
                    print("❌ Aborted")
                    return False

            # Link the user
            user.clerk_user_id = clerk_user_id
            await session.commit()
            await session.refresh(user)

            print(f"✅ Successfully linked user {email} to Clerk user {clerk_user_id}")
            print(f"   User ID: {user.id}")
            print(f"   Display Name: {user.display_name}")
            return True

        except Exception as e:
            await session.rollback()
            print(f"❌ Error linking user: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


async def main():
    parser = argparse.ArgumentParser(description="Link an existing user to Clerk")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument(
        "--clerk-user-id", required=True, help="Clerk user ID (from JWT sub claim)"
    )
    args = parser.parse_args()

    success = await link_user_to_clerk(args.email, args.clerk_user_id)
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
