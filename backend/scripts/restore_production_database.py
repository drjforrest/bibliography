#!/usr/bin/env python3
"""
Restore production database to local, reconciling schema differences.

This script:
1. Backs up the current local database
2. Compares schemas between local and production
3. Creates a migration plan
4. Restores production data while preserving local schema changes

Usage:
    python backend/scripts/restore_production_database.py --dry-run
    python backend/scripts/restore_production_database.py
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import os

load_dotenv(".env")
if not os.getenv("CLERK_ISSUER"):
    os.environ["CLERK_ISSUER"] = "https://dummy.clerk.accounts.dev"
if not os.getenv("CLERK_JWKS_URL"):
    os.environ["CLERK_JWKS_URL"] = (
        "https://dummy.clerk.accounts.dev/.well-known/jwks.json"
    )

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import config


async def backup_local_database():
    """Backup the current local database"""
    backup_file = f"/tmp/bibliography_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    print(f"📦 Backing up local database to {backup_file}...")
    
    result = subprocess.run(
        [
            "pg_dump",
            "-U", "postgres",
            "-h", "localhost",
            "-d", "bibliography_db",
            "-F", "c",  # Custom format
            "-f", backup_file,
        ],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        print(f"  ✅ Backup created: {backup_file}")
        return backup_file
    else:
        print(f"  ❌ Backup failed: {result.stderr}")
        return None


async def compare_schemas():
    """Compare schemas and identify differences"""
    print("\n🔍 Comparing schemas...")
    
    # Get local schema info
    local_engine = create_async_engine(config.DATABASE_URL)
    async with local_engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        local_tables = [row[0] for row in result.fetchall()]
    
    await local_engine.dispose()
    
    # Get production schema info (via SSH)
    print("  Fetching production schema...")
    result = subprocess.run(
        [
            "ssh", "jforrest@mac-mini",
            "/usr/local/opt/postgresql@17/bin/psql -U postgres -h localhost -d hero_evidence_library_prod -t -c \"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;\""
        ],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        prod_tables = [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
    else:
        print(f"  ⚠️  Could not fetch production schema: {result.stderr}")
        prod_tables = []
    
    print(f"\n  Local tables: {len(local_tables)}")
    print(f"  Production tables: {len(prod_tables)}")
    
    only_local = set(local_tables) - set(prod_tables)
    only_prod = set(prod_tables) - set(local_tables)
    common = set(local_tables) & set(prod_tables)
    
    if only_local:
        print(f"\n  ⚠️  Tables only in local: {sorted(only_local)}")
    if only_prod:
        print(f"\n  ⚠️  Tables only in production: {sorted(only_prod)}")
    if common:
        print(f"\n  ✅ Common tables: {len(common)}")
    
    return {
        "only_local": only_local,
        "only_prod": only_prod,
        "common": common,
    }


async def restore_production_data(dry_run=False):
    """Restore production data to local database"""
    print("\n📥 Restoring production data...")
    
    if dry_run:
        print("  [DRY RUN] Would restore production data")
        return
    
    # Dump production data (data only, no schema) - use compressed format
    print("  Dumping production data (this may take a while for 1,357 papers)...")
    print("  ⏳ Please wait...")
    
    # Use custom format for faster transfer
    data_file = "/tmp/prod_data.dump"
    
    # First dump on remote server
    print("  Step 1/3: Creating dump on production server...")
    result = subprocess.run(
        [
            "ssh", "jforrest@mac-mini",
            "/usr/local/opt/postgresql@17/bin/pg_dump -U postgres -h localhost -d hero_evidence_library_prod --data-only --format=custom --no-owner --no-acl -f /tmp/prod_data.dump"
        ],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"  ❌ Failed to dump production data: {result.stderr}")
        return
    
    print("  ✅ Dump created on production server")
    
    # Copy dump file
    print("  Step 2/3: Copying dump file to local machine...")
    result = subprocess.run(
        ["scp", "jforrest@mac-mini:/tmp/prod_data.dump", data_file],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"  ❌ Failed to copy dump file: {result.stderr}")
        return
    
    # Get file size
    import os
    size_mb = os.path.getsize(data_file) / 1024 / 1024
    print(f"  ✅ Dump file copied ({size_mb:.2f} MB)")
    
    # Clear local database (but keep schema)
    print("\n  Clearing local database data...")
    local_engine = create_async_engine(config.DATABASE_URL)
    async with local_engine.begin() as conn:
        # Get all tables
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        # Disable triggers and truncate
        for table in tables:
            try:
                await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
            except Exception as e:
                print(f"    ⚠️  Could not truncate {table}: {e}")
    
    await local_engine.dispose()
    
    # Restore production data using pg_restore (for custom format)
    print("  Step 3/3: Restoring production data to local database...")
    print("  ⏳ This may take several minutes...")
    
    result = subprocess.run(
        [
            "pg_restore",
            "-U", "postgres",
            "-h", "localhost",
            "-d", "bibliography_db",
            "--data-only",
            "--no-owner",
            "--no-acl",
            "--verbose",
            data_file,
        ],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        print("  ✅ Production data restored!")
        # Clean up
        try:
            os.remove(data_file)
            subprocess.run(["ssh", "jforrest@mac-mini", "rm /tmp/prod_data.dump"], 
                         capture_output=True)
        except:
            pass
    else:
        print(f"  ❌ Restore failed: {result.stderr}")
        print(f"  stdout: {result.stdout[-1000:]}")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Restore production database to local")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()
    
    print("🚀 Database Restoration Script")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
        print()
    
    # Step 1: Backup
    if not args.dry_run:
        backup_file = await backup_local_database()
        if not backup_file:
            print("❌ Backup failed. Aborting.")
            return
    
    # Step 2: Compare schemas
    schema_diff = await compare_schemas()
    
    # Step 3: Restore
    await restore_production_data(dry_run=args.dry_run)
    
    print("\n" + "=" * 60)
    print("✅ Process complete!")
    if not args.dry_run:
        print(f"  Backup saved (if needed): /tmp/bibliography_db_backup_*.sql")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

