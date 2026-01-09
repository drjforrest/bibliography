#!/usr/bin/env python3
"""Detailed test of SSH tunnel to see what database we're actually connecting to"""

import asyncio
import os
import socket

import asyncpg


async def test_tunnel():
    print("=" * 60)
    print("SSH TUNNEL DETAILED DIAGNOSTICS")
    print("=" * 60)

    # First, let's test what port 5433 actually connects to
    print("\n1. Testing raw connection to 127.0.0.1:5433...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", 5433))
        sock.close()
        if result == 0:
            print("   ✓ Port 5433 is open and accepting connections")
        else:
            print(f"   ✗ Cannot connect to port 5433 (error: {result})")
            return
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    # Now try asyncpg connection
    print("\n2. Testing asyncpg connection through tunnel (127.0.0.1:5433)...")
    try:
        conn = await asyncpg.connect(
            host="127.0.0.1",
            port=5433,
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "hero_evidence_library_prod"),
            timeout=5,
        )

        # Get connection info
        version = await conn.fetchval("SELECT version()")
        server_addr = await conn.fetchval("SELECT inet_server_addr()")
        server_port = await conn.fetchval("SELECT inet_server_port()")
        db_name = await conn.fetchval("SELECT current_database()")
        session_pid = await conn.fetchval("SELECT pg_backend_pid()")

        print("\n   Connection details:")
        print(f"   - Database: {db_name}")
        print(f"   - PostgreSQL version: {version[:60]}...")
        print(f"   - Server address (from DB): {server_addr}")
        print(f"   - Server port (from DB): {server_port}")
        print(f"   - Backend PID: {session_pid}")

        # Try to get hostname from the server
        try:
            hostname = await conn.fetchval(
                "SELECT hostname FROM pg_stat_activity WHERE pid = pg_backend_pid()"
            )
            print(f"   - Hostname: {hostname}")
        except Exception:
            pass

        # Check if it's local or remote by examining the version string
        if "Homebrew" in version and "x86_64-apple-darwin23.6.0" in version:
            print("\n   ⚠️  This appears to be the LOCAL Homebrew PostgreSQL!")
            print("   The SSH tunnel may not be forwarding correctly.")
        else:
            print("\n   ✓ This appears to be the REMOTE production database!")

        # Try to count records to verify it's production
        try:
            paper_count = await conn.fetchval("SELECT COUNT(*) FROM scientific_papers")
            print(f"\n   📊 Papers in database: {paper_count}")

            # Check if we can see the sync table
            sync_count = await conn.fetchval("""
                SELECT COUNT(*) FROM devonthink_sync 
                WHERE sync_status::text = 'SYNCED'
            """)
            print(f"   📊 Synced records: {sync_count}")
        except Exception as e:
            print(f"\n   ⚠️  Could not query records: {e}")

        await conn.close()

    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tunnel())
