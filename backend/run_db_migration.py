import asyncio
import sys
from app.db import create_db_and_tables

async def main():
    print("  Creating v2 tables...")
    try:
        await create_db_and_tables()
        print("  ✅ Tables created successfully")
        return 0
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
