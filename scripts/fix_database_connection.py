#!/usr/bin/env python3
"""
Database Setup and Verification Script for HERO Evidence Library v1

This script:
1. Tests database connection
2. Verifies table structure
3. Provides diagnostic information

Usage:
    python scripts/fix_database_connection.py

Configuration:
    Update DATABASE_URL in your .env file with:
    DATABASE_URL="postgresql+asyncpg://jforrest:Forrest14$@192.168.1.69:5432/hero_evidence_library_prod"
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


# Database connection string
# Update this to match your v1 database configuration
DATABASE_URL = "postgresql+asyncpg://jforrest:Forrest14$@192.168.1.69:5432/hero_evidence_library_prod"


async def test_connection():
    """Test basic database connectivity."""
    print("\n" + "="*60)
    print("STEP 1: Testing Database Connection")
    print("="*60)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text('SELECT version()'))
            version = result.scalar()
            print(f"✅ Connection successful!")
            print(f"   Server: 192.168.1.69:5432")
            print(f"   Database: hero_evidence_library_prod")
            print(f"   PostgreSQL: {version[:60]}...")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"\nError details: {type(e).__name__}")
        return False
    finally:
        await engine.dispose()


async def verify_tables():
    """Verify existing table structure."""
    print("\n" + "="*60)
    print("STEP 2: Verifying Existing Tables")
    print("="*60)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Get all table names
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = [row[0] for row in result]
            
            print(f"\n📋 Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
            
            return tables
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return []
    finally:
        await engine.dispose()


async def check_key_tables():
    """Check critical table schemas."""
    print("\n" + "="*60)
    print("STEP 3: Checking Key Table Schemas")
    print("="*60)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Check user table
            result = await conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'user' AND column_name = 'id'"
            ))
            user_id_info = list(result)
            if user_id_info:
                col_name, col_type = user_id_info[0]
                print(f"\n✓ user.id type: {col_type}")
                if col_type != "uuid":
                    print(f"   ⚠️  WARNING: Expected UUID, got {col_type}")
            else:
                print("\n⚠️  Could not find user table or id column")
            
            # Check scientific_papers table if it exists
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'scientific_papers')"
            ))
            if result.scalar():
                result = await conn.execute(text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = 'scientific_papers' AND column_name = 'id'"
                ))
                paper_id_info = list(result)
                if paper_id_info:
                    col_name, col_type = paper_id_info[0]
                    print(f"✓ scientific_papers.id type: {col_type}")
            
            return True
    except Exception as e:
        print(f"❌ Error checking schemas: {e}")
        return False
    finally:
        await engine.dispose()


async def get_table_details(table_name: str):
    """Get detailed information about a specific table."""
    print(f"\n📋 Table: {table_name}")
    print("-" * 60)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Get column information
            result = await conn.execute(text(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{table_name}' "
                f"ORDER BY ordinal_position"
            ))
            
            print(f"{'Column':30} {'Type':20} {'Nullable':10}")
            print("-" * 60)
            for col_name, col_type, nullable in result:
                print(f"{col_name:30} {col_type:20} {nullable:10}")
    except Exception as e:
        print(f"❌ Error getting table details: {e}")
    finally:
        await engine.dispose()


async def main():
    """Run all database setup and verification steps."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  HERO Evidence Library v1 - Database Check Script".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # Step 1: Test connection
    if not await test_connection():
        print("\n❌ Cannot proceed without database connection")
        print("\n🔧 Troubleshooting Steps:")
        print("1. Verify mac-mini is accessible at 192.168.1.69")
        print("   Test: ping 192.168.1.69")
        print("\n2. Verify PostgreSQL is running on port 5432")
        print("   Test: telnet 192.168.1.69 5432")
        print("\n3. Verify credentials: jforrest / Forrest14$")
        print("   - Username: jforrest")
        print("   - Password: Forrest14$ (dollar sign NOT escaped)")
        print("\n4. Check .env file has correct DATABASE_URL:")
        print('   DATABASE_URL="postgresql+asyncpg://jforrest:Forrest14$@192.168.1.69:5432/hero_evidence_library_prod"')
        print("\n5. Ensure asyncpg is installed:")
        print("   pip install asyncpg")
        return
    
    # Step 2: Verify tables
    tables = await verify_tables()
    
    if not tables:
        print("\n❌ No tables found or error accessing database")
        return
    
    # Step 3: Check key schemas
    await check_key_tables()
    
    # Step 4: Offer to show specific table details
    print("\n" + "="*60)
    print("Table Detail Inspector")
    print("="*60)
    print("\nWould you like to inspect a specific table?")
    print("Enter table name (or press Enter to skip): ", end="")
    
    try:
        table_choice = input().strip()
        if table_choice and table_choice in tables:
            await get_table_details(table_choice)
        elif table_choice:
            print(f"⚠️  Table '{table_choice}' not found")
    except EOFError:
        # Running in non-interactive mode
        pass
    
    # Final summary
    print("\n" + "="*60)
    print("✅ DATABASE CHECK COMPLETE")
    print("="*60)
    print("\n📝 Connection String (for .env):")
    print('DATABASE_URL="postgresql+asyncpg://jforrest:Forrest14$@192.168.1.69:5432/hero_evidence_library_prod"')
    print("\n💡 Pro Tips:")
    print("- Use IP address (192.168.1.69) instead of hostname")
    print("- Password dollar sign is NOT escaped in connection string")
    print("- Use 'asyncpg' driver for async SQLAlchemy")
    print("- Test connection before running migrations")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
