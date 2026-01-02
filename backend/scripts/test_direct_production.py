#!/usr/bin/env python3
"""Test direct connection to production server"""

import asyncio
import os
import sys

import asyncpg


def get_env_var(name: str, default: str = None) -> str:
    """Get environment variable with validation."""
    value = os.environ.get(name, default)
    if value is None:
        print(f"✗ Error: Required environment variable '{name}' is not set")
        print("\n💡 Please set the following environment variables:")
        print("   - PG_HOST (database host, e.g., 192.168.1.69)")
        print("   - PG_PORT (database port, default: 5432)")
        print("   - PG_USER (database username)")
        print("   - PG_PASSWORD (database password)")
        print("   - PG_DATABASE (database name)")
        sys.exit(1)
    return value


async def test():
    # Get connection parameters from environment variables
    host = get_env_var("PG_HOST")
    port = int(get_env_var("PG_PORT", "5432"))
    user = get_env_var("PG_USER")
    password = get_env_var("PG_PASSWORD")
    database = get_env_var("PG_DATABASE")

    print(f"Testing DIRECT connection to production ({host}:{port})...")
    print("=" * 60)

    try:
        # Connect directly to production server using async context manager
        async with asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            timeout=10,  # Longer timeout for network connection
        ) as conn:
            # Get server info
            version = await conn.fetchval("SELECT version()")
            server_addr = await conn.fetchval("SELECT inet_server_addr()")
            server_port = await conn.fetchval("SELECT inet_server_port()")
            db_name = await conn.fetchval("SELECT current_database()")

            print("✓ Connected successfully!")
            print(f"  Database: {db_name}")
            print(f"  Server address: {server_addr or 'N/A'}")
            print(f"  Server port: {server_port or 'N/A'}")
            print(f"  PostgreSQL version: {version[:80]}...")
            print()

            if "Homebrew" in version:
                print("💻 LOCAL database (Homebrew PostgreSQL)")
                print("   ⚠️  This shouldn't happen with direct IP")
            else:
                print("🌐 REMOTE connection (mac-mini production)")
                print("   ✓ Direct connection working!")

            # Try to count records (handle enum issue)
            try:
                # Try different enum values
                synced = await conn.fetchval(
                    "SELECT COUNT(*) FROM devonthink_sync WHERE sync_status::text = $1",
                    "SYNCED",
                )
                papers = await conn.fetchval("SELECT COUNT(*) FROM scientific_papers")

                print("\n📊 Database contents:")
                print(f"   ✅ Synced records: {synced}")
                print(f"   📄 Total papers: {papers}")
            except Exception as e:
                print(f"\n⚠️  Could not query records: {e}")
                print("   (This might indicate a schema mismatch)")

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check if PostgreSQL is running on mac-mini")
        print("   - Verify firewall allows connections from MacBook")
        print("   - Check pg_hba.conf allows network connections")


if __name__ == "__main__":
    asyncio.run(test())
