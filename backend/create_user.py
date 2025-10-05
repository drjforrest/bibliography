#!/usr/bin/env python3
"""
Script to create a user directly in the database
"""

import asyncio
import getpass
import sys
from uuid import uuid4

from app.db import get_async_session_context, User, SearchSpace
from app.users import get_user_manager


async def create_user():
    """Create a new user with a default search space"""
    
    # Get user input
    email = input("Enter email address: ").strip()
    if not email:
        print("❌ Email is required")
        return
    
    password = getpass.getpass("Enter password: ").strip()
    if not password:
        print("❌ Password is required")
        return
    
    print(f"\nCreating user with email: {email}")
    
    try:
        async with get_async_session_context() as session:
            # Check if user already exists
            from sqlalchemy import select
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"❌ User with email {email} already exists")
                print(f"   User ID: {existing_user.id}")
                return existing_user.id
            
            # Create user
            user_dict = {
                "email": email,
                "password": password,
                "is_active": True,
                "is_superuser": False,
                "is_verified": True
            }
            
            # Use the user manager to create user with proper password hashing
            from fastapi_users.schemas import BaseUserCreate
            from app.schemas import UserCreate
            
            user_create = UserCreate(**user_dict)
            
            # Get user manager
            user_manager = get_user_manager()
            
            # Create the user
            user = await user_manager.create(user_create)
            
            print(f"✅ User created successfully!")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            
            # Create a default search space for the user
            search_space = SearchSpace(
                name="My Research Library",
                description="Default search space for DEVONthink migration",
                user_id=user.id,
                is_public=False
            )
            
            session.add(search_space)
            await session.commit()
            
            print(f"✅ Created default search space: '{search_space.name}' (ID: {search_space.id})")
            
            return user.id
            
    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        return None


async def list_users():
    """List existing users"""
    try:
        async with get_async_session_context() as session:
            from sqlalchemy import select
            stmt = select(User.id, User.email, User.is_active).limit(10)
            result = await session.execute(stmt)
            users = result.fetchall()
            
            if not users:
                print("No users found in database")
                return
            
            print("Existing users:")
            for user in users:
                status = "✅ Active" if user.is_active else "❌ Inactive"
                print(f"  {status} - ID: {user.id}, Email: {user.email}")
                
    except Exception as e:
        print(f"❌ Error listing users: {str(e)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="User management for bibliography system")
    parser.add_argument("--list", "-l", action="store_true", help="List existing users")
    parser.add_argument("--create", "-c", action="store_true", help="Create a new user")
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_users())
    elif args.create:
        user_id = asyncio.run(create_user())
        if user_id:
            print(f"\n🚀 Ready to start migration! Use this User ID: {user_id}")
    else:
        print("Use --list to see users or --create to create a new user")


if __name__ == "__main__":
    main()