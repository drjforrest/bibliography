"""
Migration script to add clerk_user_id column to User table.

Run this script to add Clerk integration support to existing database.
"""
import asyncio
from sqlalchemy import text
from app.db import engine


async def add_clerk_user_id_column():
    """Add clerk_user_id column to user table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema='public' AND table_name='user' AND column_name='clerk_user_id'
        """))
        
        if result.fetchone() is None:
            print("Adding clerk_user_id column to user table...")
            await conn.execute(text("""
                ALTER TABLE "user" 
                ADD COLUMN clerk_user_id VARCHAR(255) UNIQUE
            """))
            
            # Add index for faster lookups
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_clerk_user_id 
                ON "user" (clerk_user_id)
            """))
            
            print("✓ Successfully added clerk_user_id column and index")
        else:
            print("✓ clerk_user_id column already exists")


async def main():
    """Run the migration."""
    print("Starting Clerk migration...")
    try:
        await add_clerk_user_id_column()
        print("\n✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Add CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY, and CLERK_WEBHOOK_SECRET")
        print("   to your .env file (see .env.example for details)")
        print("2. Restart your backend server")
        print("3. Configure Clerk webhook in Clerk Dashboard to point to: http://yourserver/webhooks/clerk")
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
