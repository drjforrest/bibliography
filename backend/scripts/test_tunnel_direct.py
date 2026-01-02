#!/usr/bin/env python3
"""Direct test of SSH tunnel to verify it's working"""
import asyncio
import asyncpg
import sys

async def test():
    print("Testing direct connection through SSH tunnel (localhost:5433)...")
    print("="*60)
    
    try:
        # Try connecting directly via asyncpg to port 5433
        # Force IPv4 to avoid IPv6 localhost issues
        conn = await asyncpg.connect(
            host='127.0.0.1',  # Use IPv4 explicitly, not 'localhost' (which can use IPv6)
            port=5433,  # SSH tunnel port
            user='postgres',
            password='postgres',
            database='hero_evidence_library_prod',
            timeout=5
        )
        
        # Get server info
        version = await conn.fetchval('SELECT version()')
        server_addr = await conn.fetchval('SELECT inet_server_addr()')
        server_port = await conn.fetchval('SELECT inet_server_port()')
        db_name = await conn.fetchval('SELECT current_database()')
        
        print(f"✓ Connected successfully!")
        print(f"  Database: {db_name}")
        print(f"  Server address: {server_addr or 'N/A (local)'}")
        print(f"  Server port: {server_port or 'N/A (local)'}")
        print(f"  PostgreSQL version: {version[:60]}...")
        print()
        
        if server_addr:
            print("🌐 REMOTE connection (mac-mini production)")
            print("   ✓ SSH tunnel is working correctly!")
        elif server_port:
            print(f"💻 Connected via tunnel but showing local port {server_port}")
            print("   ⚠️  May be local database with same name")
        elif "Homebrew" in version:
            print("💻 LOCAL connection (Homebrew PostgreSQL on MacBook)")
            print("   ❌ SSH tunnel not being used - connecting to local DB")
        else:
            print("🤔 Unclear connection status")
        
        # Count records
        synced = await conn.fetchval(
            'SELECT COUNT(*) FROM devonthink_sync WHERE sync_status = $1',
            'synced'
        )
        papers = await conn.fetchval('SELECT COUNT(*) FROM scientific_papers')
        
        print(f"\n📊 Database contents:")
        print(f"   ✅ Synced records: {synced}")
        print(f"   📄 Total papers: {papers}")
        
        await conn.close()
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\n   This could mean:")
        print("   - SSH tunnel isn't forwarding correctly")
        print("   - PostgreSQL isn't running on mac-mini")
        print("   - Wrong database name or credentials")

if __name__ == "__main__":
    asyncio.run(test())

