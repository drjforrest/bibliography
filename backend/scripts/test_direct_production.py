#!/usr/bin/env python3
"""Test direct connection to production server at 192.168.1.69"""

import asyncio
import sys

import asyncpg


async def test():
    print("Testing DIRECT connection to production (192.168.1.69:5432)...")
    print("=" * 60)

    try:
        # Connect directly to production server
        conn = await asyncpg.connect(
            host="192.168.1.69",  # Direct IP to mac-mini
            port=5432,  # PostgreSQL port on production
            user="postgres",
            password="postgres",
            database="hero_evidence_library_prod",
            timeout=10,  # Longer timeout for network connection
        )

        # Get server info
        version = await conn.fetchval("SELECT version()")
        server_addr = await conn.fetchval("SELECT inet_server_addr()")
        server_port = await conn.fetchval("SELECT inet_server_port()")
        db_name = await conn.fetchval("SELECT current_database()")

        print(f"✓ Connected successfully!")
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
                "SYNCED"
            )
            papers = await conn.fetchval("SELECT COUNT(*) FROM scientific_papers")

            print(f"\n📊 Database contents:")
            print(f"   ✅ Synced records: {synced}")
            print(f"   📄 Total papers: {papers}")
        except Exception as e:
            print(f"\n⚠️  Could not query records: {e}")
            print("   (This might indicate a schema mismatch)")

        await conn.close()

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check if PostgreSQL is running on mac-mini")
        print("   - Verify firewall allows connections from MacBook")
        print("   - Check pg_hba.conf allows network connections")


if __name__ == "__main__":
    asyncio.run(test())

