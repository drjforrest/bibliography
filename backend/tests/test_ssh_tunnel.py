#!/usr/bin/env python3
"""
Test if SSH tunnel on port 5433 is actually forwarding to mac-mini
"""

import os
import socket
import sys


def get_env_var(name: str, default: str = None) -> str:
    """Get environment variable with validation."""
    value = os.environ.get(name, default)
    if value is None:
        print(f"✗ Error: Required environment variable '{name}' is not set")
        print("\n💡 Please set the following environment variables:")
        print("   - DB_HOST (database host, default: localhost)")
        print("   - DB_PORT (database port, default: 5433)")
        print("   - DB_USER (database username, default: postgres)")
        print("   - DB_PASSWORD (database password)")
        print("   - DB_NAME (database name, default: hero_evidence_library_prod)")
        sys.exit(1)
    return value


def test_port(host, port):
    """Test if a port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error testing {host}:{port}: {e}")
        return False


print("Testing SSH tunnel connection...")
print("=" * 60)

# Test local port 5433 (should be SSH tunnel)
if test_port("localhost", 5433):
    print("✓ Port 5433 is open and accepting connections")

    # Try to connect and see what we get
    try:
        import asyncio

        import asyncpg

        async def test():
            try:
                # Try connecting via asyncpg
                conn = await asyncpg.connect(
                    host=os.getenv("DB_HOST", "localhost"),
                    port=int(os.getenv("DB_PORT", "5433")),
                    user=os.getenv("DB_USER", "postgres"),
                    password=get_env_var("DB_PASSWORD"),
                    database=os.getenv("DB_NAME", "hero_evidence_library_prod"),
                    timeout=5,
                )

                # Get server info
                version = await conn.fetchval("SELECT version()")
                server_addr = await conn.fetchval("SELECT inet_server_addr()")
                server_port = await conn.fetchval("SELECT inet_server_port()")

                print("✓ Connected successfully!")
                print(f"  Server address: {server_addr or 'localhost'}")
                print(f"  Server port: {server_port}")
                print(f"  PostgreSQL: {version[:60]}...")

                if server_addr:
                    print("\n🌐 This is REMOTE (mac-mini via SSH tunnel)")
                elif "Homebrew" in version:
                    print("\n💻 This is LOCAL (Homebrew PostgreSQL)")
                    print("   ⚠️  SSH tunnel may not be forwarding correctly")
                else:
                    print("\n🤔 Connection info unclear")

                await conn.close()

            except Exception as e:
                print(f"✗ Connection failed: {e}")
                print(
                    "   This suggests the SSH tunnel isn't working or PostgreSQL isn't accessible"
                )

        asyncio.run(test())

    except ImportError:
        print("⚠️  asyncpg not available, cannot test full connection")
        print("   But port 5433 is open, so SSH tunnel appears to be active")
else:
    print("✗ Port 5433 is NOT accessible")
    print("   SSH tunnel may not be running")
    print("\n   To set up tunnel, run:")
    print("   ssh -L 5433:localhost:5432 mac-mini")
    print("   (keep that terminal open)")
