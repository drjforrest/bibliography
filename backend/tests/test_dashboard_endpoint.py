#!/usr/bin/env python3
"""
Test script to diagnose dashboard endpoint issues.
This will help identify what's causing the dashboard error.
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, '.')

from app.db import get_async_session_context
from app.services.dashboard_service import DashboardService
from app.config import config


async def test_dashboard():
    """Test the dashboard service with a real user."""
    print("🔍 Testing Dashboard Service")
    print("=" * 50)
    
    try:
        # Get a user from the database
        async with get_async_session_context() as session:
            from sqlalchemy import select
            from app.db import User
            
            # Get first user
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ No users found in database")
                return
            
            print(f"✅ Found user: {user.email} (ID: {user.id})")
            print(f"   Clerk User ID: {user.clerk_user_id}")
            print(f"   Last Login: {user.last_login}")
            print()
            
            # Test the dashboard service
            print("📊 Testing get_literature_type_stats...")
            dashboard_service = DashboardService(session)
            
            try:
                stats = await dashboard_service.get_literature_type_stats(str(user.id))
                print("✅ Dashboard stats retrieved successfully!")
                print(f"   Total Papers: {stats.total_papers}")
                print(f"   Literature Types: {len(stats.by_literature_type)}")
                print(f"   New Since Last Login: {stats.new_since_last_login_count}")
                print(f"   Last Login: {stats.last_login}")
                print()
                
                # Print literature type breakdown
                for lit_type in stats.by_literature_type:
                    print(f"   - {lit_type.label}: {lit_type.count}")
                
            except Exception as e:
                print(f"❌ Error getting dashboard stats: {str(e)}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_dashboard())

