#!/usr/bin/env python3
"""
Reset user password.

Usage:
    python scripts/reset_password.py --email user@example.com --password newpassword
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db import User
from app.config import config
from app.users import get_user_manager
from fastapi_users.password import PasswordHelper


async def reset_password(email: str, new_password: str):
    """Reset a user's password."""

    engine = create_async_engine(config.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find user
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            print(f"User not found: {email}")
            return False

        # Hash the new password
        password_helper = PasswordHelper()
        hashed_password = password_helper.hash(new_password)

        # Update password
        user.hashed_password = hashed_password
        await session.commit()

        print(f"Password reset successfully for: {email}")
        print(f"New password: {new_password}")
        return True

    await engine.dispose()


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Reset user password')
    parser.add_argument('--email', required=True, help='User email')
    parser.add_argument('--password', required=True, help='New password')
    args = parser.parse_args()

    await reset_password(args.email, args.password)


if __name__ == "__main__":
    asyncio.run(main())
