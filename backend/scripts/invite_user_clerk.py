"""
Script to invite a user to the application (Clerk-based invite-only system).

This script creates a user in the database that can then authenticate via Clerk.
Users must be created here before they can sign in through Clerk.

Usage:
    # Basic invite (email + Clerk user ID required)
    python scripts/invite_user_clerk.py --email user@example.com --clerk-user-id user_abc123

    # Full invite with profile info
    python scripts/invite_user_clerk.py \
        --email user@example.com \
        --clerk-user-id user_abc123 \
        --first-name John \
        --last-name Doe \
        --avatar-url https://example.com/avatar.jpg

    # List all users
    python scripts/invite_user_clerk.py --list
"""

import argparse
import asyncio
import secrets
import string

from app.db import User, SearchSpace, get_async_session_context
from sqlalchemy import select


async def invite_user(
    email: str,
    clerk_user_id: str,
    first_name: str | None = None,
    last_name: str | None = None,
    avatar_url: str | None = None,
) -> bool:
    """
    Create an invited user in the database.

    Args:
        email: User's email address
        clerk_user_id: Clerk user ID (from Clerk dashboard, e.g., "user_abc123")
        first_name: Optional first name
        last_name: Optional last name
        avatar_url: Optional profile image URL

    Returns:
        True if user was created successfully, False otherwise
    """
    async with get_async_session_context() as session:
        try:
            # Check if user already exists by email
            result = await session.execute(select(User).where(User.email == email))
            existing_by_email = result.scalar_one_or_none()

            if existing_by_email:
                print(f"❌ User with email {email} already exists")
                print(f"   User ID: {existing_by_email.id}")
                print(f"   Clerk User ID: {existing_by_email.clerk_user_id or 'Not linked'}")
                return False

            # Check if user already exists by Clerk ID
            result = await session.execute(
                select(User).where(User.clerk_user_id == clerk_user_id)
            )
            existing_by_clerk = result.scalar_one_or_none()

            if existing_by_clerk:
                print(f"❌ User with Clerk ID {clerk_user_id} already exists")
                print(f"   User ID: {existing_by_clerk.id}")
                print(f"   Email: {existing_by_clerk.email}")
                return False

            # Generate a random password to satisfy database schema requirements
            # 
            # NOTE: This password is NEVER used or checked. Clerk handles all authentication.
            # The fastapi-users library's SQLAlchemyBaseUserTableUUID base table requires
            # a hashed_password field (NOT NULL), so we must provide a value even though
            # it's completely ignored. We generate a secure random password that will
            # never be validated or used.
            password_length = 64
            alphabet = string.ascii_letters + string.digits + string.punctuation
            random_password = "".join(secrets.choice(alphabet) for _ in range(password_length))

            # Create display name from first/last name if provided
            display_name = None
            if first_name or last_name:
                display_name = f"{first_name or ''} {last_name or ''}".strip()

            # Create user using the user manager (handles password hashing)
            from app.users import get_user_manager
            from app.schemas import UserCreate

            user_manager = get_user_manager()
            user_create = UserCreate(
                email=email,
                password=random_password,  # Placeholder - never used (Clerk handles auth)
                is_active=True,
                is_superuser=False,
                is_verified=True,  # Clerk handles email verification
            )

            user = await user_manager.create(user_create)

            # Update Clerk-specific fields
            user.clerk_user_id = clerk_user_id
            if display_name:
                user.display_name = display_name
            if avatar_url:
                user.avatar_url = avatar_url

            await session.commit()
            await session.refresh(user)

            print("✅ User invited successfully!")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Clerk User ID: {user.clerk_user_id}")
            if user.display_name:
                print(f"   Display Name: {user.display_name}")

            # Create a default search space for the user
            search_space = SearchSpace(
                name="My Research Library",
                description="Default search space",
                user_id=user.id,
                is_public=False,
            )

            session.add(search_space)
            await session.commit()

            print(f"✅ Created default search space: '{search_space.name}' (ID: {search_space.id})")
            print(f"\n🚀 User can now sign in via Clerk with email: {email}")

            return True

        except Exception as e:
            await session.rollback()
            print(f"❌ Error inviting user: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


async def list_users():
    """List all users in the database."""
    async with get_async_session_context() as session:
        try:
            result = await session.execute(
                select(
                    User.id,
                    User.email,
                    User.clerk_user_id,
                    User.display_name,
                    User.is_active,
                ).order_by(User.email)
            )
            users = result.fetchall()

            if not users:
                print("No users found in database")
                return

            print(f"\n{'Email':<40} {'Clerk ID':<30} {'Display Name':<25} {'Status'}")
            print("-" * 110)
            for user in users:
                status = "✅ Active" if user.is_active else "❌ Inactive"
                clerk_id = user.clerk_user_id or "Not linked"
                display_name = user.display_name or "-"
                print(
                    f"{user.email:<40} {clerk_id:<30} {display_name:<25} {status}"
                )

        except Exception as e:
            print(f"❌ Error listing users: {str(e)}")
            import traceback

            traceback.print_exc()


async def main():
    parser = argparse.ArgumentParser(
        description="Invite users to the Clerk-based invite-only application"
    )
    parser.add_argument("--email", help="User email address")
    parser.add_argument(
        "--clerk-user-id",
        help="Clerk user ID (from Clerk dashboard, e.g., 'user_abc123')",
    )
    parser.add_argument("--first-name", help="User's first name (optional)")
    parser.add_argument("--last-name", help="User's last name (optional)")
    parser.add_argument("--avatar-url", help="User's profile image URL (optional)")
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all users in the database",
    )

    args = parser.parse_args()

    if args.list:
        await list_users()
    elif args.email and args.clerk_user_id:
        success = await invite_user(
            email=args.email,
            clerk_user_id=args.clerk_user_id,
            first_name=args.first_name,
            last_name=args.last_name,
            avatar_url=args.avatar_url,
        )
        exit(0 if success else 1)
    else:
        parser.print_help()
        print("\n❌ Error: --email and --clerk-user-id are required for inviting users")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

