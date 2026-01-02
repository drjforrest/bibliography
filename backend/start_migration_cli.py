#!/usr/bin/env python3
"""
CLI script to start DEVONthink migration using the Enhanced Migration Service
"""

import argparse
import asyncio
import logging
import os
import sys
from uuid import UUID

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.enhanced_migration_service import EnhancedMigrationService
from app.db import get_async_session_context, SearchSpace
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


async def create_default_search_space(session, user_id: UUID):
    """Get or create a default search space for DEVONthink migration"""
    stmt = select(SearchSpace).where(SearchSpace.user_id == user_id).order_by(SearchSpace.id)
    result = await session.execute(stmt)
    existing_spaces = result.scalars().all()

    if existing_spaces:
        # Use the first existing search space (prefer one named "DEVONthink Migration" if it exists)
        for space in existing_spaces:
            if "DEVONthink" in space.name or "Migration" in space.name:
                logger.info(f"Using existing search space: {space.name} (ID: {space.id})")
                return space.id
        
        # Otherwise use the first one
        first_space = existing_spaces[0]
        logger.info(f"Using existing search space: {first_space.name} (ID: {first_space.id})")
        return first_space.id

    # Create default search space if none exists
    search_space = SearchSpace(
        name="DEVONthink Migration",
        description="Automatically created for DEVONthink migration",
        user_id=user_id,
    )
    session.add(search_space)
    await session.commit()

    logger.info(
        f"Created new search space: {search_space.name} (ID: {search_space.id})"
    )
    return search_space.id


async def start_migration(
    database_name: str,
    user_id: str,
    folder_path: str = None,
    force_resync: bool = False,
    redis_url: str = None,
    search_space_id: int = None,
):
    """Start the enhanced migration process"""

    logger.info("🚀 Starting DEVONthink Enhanced Migration")
    logger.info("=" * 60)

    try:
        # Convert user_id string to UUID
        user_uuid = UUID(user_id)
        logger.info(f"📚 Database: {database_name}")
        logger.info(f"👤 User ID: {user_uuid}")
        logger.info(f"📁 Folder Path: {folder_path or 'All folders'}")
        logger.info(f"🔄 Force Resync: {force_resync}")
        logger.info(f"📡 Redis URL: {redis_url or 'redis://localhost:6379/0'}")
        logger.info("=" * 60)

        # Create database session
        async with get_async_session_context() as session:
            # Get or create search space
            if search_space_id:
                # Validate the provided search space exists and belongs to user
                stmt = select(SearchSpace).where(
                    SearchSpace.id == search_space_id,
                    SearchSpace.user_id == user_uuid
                )
                result = await session.execute(stmt)
                space = result.scalar_one_or_none()
                if not space:
                    logger.error(f"Search space {search_space_id} not found or not accessible")
                    return False
                final_search_space_id = space.id
                logger.info(f"Using specified search space: {space.name} (ID: {final_search_space_id})")
            else:
                # Use default search space logic
                final_search_space_id = await create_default_search_space(session, user_uuid)

            # Initialize enhanced migration service
            migration_service = EnhancedMigrationService(session, redis_url)

            # Start the complete migration
            job_id = await migration_service.start_complete_migration(
                database_name=database_name,
                user_id=user_uuid,
                search_space_id=final_search_space_id,
                folder_path=folder_path,
                force_resync=force_resync,
            )

            logger.info(f"📋 Migration job started with ID: {job_id}")
            logger.info("👀 Watch the logs above for detailed progress...")

            # Monitor progress
            logger.info("🔍 Monitoring migration progress...")

            while True:
                try:
                    status = await migration_service.get_migration_status(job_id)

                    if not status:
                        logger.error("❌ Could not retrieve migration status")
                        break

                    phase = status.get("phase", "unknown")
                    # get_job_stats returns completed_records and total_records directly
                    completed = status.get("completed_records", 0)
                    total = status.get("total_records", 0)
                    failed = status.get("failed_records", 0)
                    pending = status.get("pending_records", 0)

                    logger.info(f"📊 Current job status: {phase}")
                    logger.info(f"📈 Progress: {completed}/{total} records")
                    if failed > 0:
                        logger.info(f"   ⚠️  Failed: {failed} records")
                    if pending > 0:
                        logger.info(f"   ⏳ Pending: {pending} records")

                    # Check if completed
                    if phase in ["completed", "failed"]:
                        if phase == "completed":
                            logger.info("✅ Migration completed successfully")
                        else:
                            logger.error("❌ Migration failed")
                            error_msg = status.get("error_message", "Unknown error")
                            logger.error(f"Error: {error_msg}")
                        break

                    # Wait before next check
                    await asyncio.sleep(5)

                except KeyboardInterrupt:
                    logger.info("\n⏸️  Migration monitoring interrupted by user")
                    logger.info("📋 Migration continues running in the background")
                    logger.info(f"🔍 Job ID: {job_id} (use this to check status later)")
                    break
                except Exception as e:
                    logger.error(f"Error monitoring migration: {str(e)}")
                    await asyncio.sleep(5)

            # Cleanup
            await migration_service.cleanup()

    except Exception as e:
        logger.error(f"❌ Migration failed to start: {str(e)}")
        logger.error(f"📋 Error type: {type(e).__name__}")
        return False

    return True


async def check_migration_status(job_id: str, redis_url: str = None):
    """Check the status of a running migration"""
    logger.info(f"🔍 Checking status of migration job: {job_id}")

    try:
        async with get_async_session_context() as session:
            migration_service = EnhancedMigrationService(session, redis_url)
            status = await migration_service.get_migration_status(job_id)

            if not status:
                logger.error(f"❌ Migration job {job_id} not found")
                return

            logger.info("📊 Migration Status:")
            logger.info(f"   Phase: {status.get('phase', 'unknown')}")
            logger.info(f"   Started: {status.get('started_at', 'unknown')}")

            progress = status.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            failed = progress.get("failed", 0)

            logger.info(f"   Progress: {completed}/{total} records completed")
            if failed > 0:
                logger.info(f"   Failed: {failed} records")

            if status.get("error_message"):
                logger.error(f"   Error: {status['error_message']}")

            await migration_service.cleanup()

    except Exception as e:
        logger.error(f"Error checking migration status: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="CLI for DEVONthink Enhanced Migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start full migration
  python start_migration_cli.py --database "References" --user-id "12345678-1234-5678-9abc-123456789012"
  
  # Start migration with specific folder
  python start_migration_cli.py --database "References" --user-id "12345678-1234-5678-9abc-123456789012" --folder "/Research Papers"
  
  # Force resync of existing records
  python start_migration_cli.py --database "References" --user-id "12345678-1234-5678-9abc-123456789012" --force-resync
  
  # Check migration status
  python start_migration_cli.py --status migration_References_12345678-1234-5678-9abc-123456789012_1758300968

Prerequisites:
  1. DEVONthink must be running
  2. Redis must be running (for progress tracking)
  3. Ollama must be running (for lay summary generation)
  4. PostgreSQL database must be running
  5. Update user_id to match your user in the database
        """,
    )

    parser.add_argument(
        "--database",
        "-d",
        default="BIBLIOGRAPHY",
        help="DEVONthink database name (default: BIBLIOGRAPHY)",
    )
    parser.add_argument(
        "--user-id", "-u", required=True, help="User UUID from the database (required)"
    )
    parser.add_argument(
        "--search-space-id",
        type=int,
        help="Search space ID to use (optional, will use first available if not specified)",
    )
    parser.add_argument(
        "--folder",
        "-f",
        help="Specific folder path to migrate (optional, default: all folders)",
    )
    parser.add_argument(
        "--force-resync", action="store_true", help="Force resync of existing records"
    )
    parser.add_argument(
        "--redis-url", help="Redis connection URL (default: redis://localhost:6379/0)"
    )
    parser.add_argument("--status", "-s", help="Check status of migration job by ID")

    args = parser.parse_args()

    if args.status:
        # Check migration status
        asyncio.run(check_migration_status(args.status, args.redis_url))
    else:
        # Start migration
        if not args.user_id:
            logger.error("❌ User ID is required. Use --user-id to specify it.")
            sys.exit(1)

        success = asyncio.run(
            start_migration(
                database_name=args.database,
                user_id=args.user_id,
                folder_path=args.folder,
                force_resync=args.force_resync,
                redis_url=args.redis_url,
                search_space_id=args.search_space_id,
            )
        )

        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
