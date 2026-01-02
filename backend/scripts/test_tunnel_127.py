#!/usr/bin/env python3
"""Test SSH tunnel using 127.0.0.1 (IPv4) instead of localhost"""

import asyncio
import sys

import asyncpg


async def test():
    print("Testing SSH tunnel with IPv4 (127.0.0.1:5433)...")
    print("=" * 60)

    try:
        # Use 127.0.0.1 explicitly (IPv4) to avoid IPv6 ::1 issues
        conn = await asyncpg.connect(
            host="127.0.0.1",  # IPv4 localhost
            port=5433,  # SSH tunnel port
            user="postgres",
            password="postgres",
            database="hero_evidence_library_prod",
            timeout=5,
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

        # Determine if it's remote or local
        is_remote = server_addr and server_addr not in ["::1", "127.0.0.1", "localhost"]
        has_remote_port = server_port and server_port != 5432

        if "Homebrew" in version:
            print("💻 LOCAL database (Homebrew PostgreSQL on MacBook)")
            print("   ❌ SSH tunnel not working - connected to local DB")
        elif is_remote or has_remote_port:
            print("🌐 REMOTE connection (mac-mini production)")
            print("   ✓ SSH tunnel is working!")
        elif server_addr in ["::1", "127.0.0.1"] or not server_addr:
            print("💻 Likely LOCAL connection (localhost)")
            print("   ⚠️  Tunnel may not be forwarding correctly")
        else:
            print(
                f"🤔 Connection status unclear (addr: {server_addr}, port: {server_port})"
            )

        # Try to count records (handle enum issue)
        try:
            synced = await conn.fetchval(
                "SELECT COUNT(*) FROM devonthink_sync WHERE sync_status = $1", "synced"
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


if __name__ == "__main__":
    asyncio.run(test())
