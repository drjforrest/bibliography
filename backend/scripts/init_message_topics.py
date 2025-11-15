"""
Script to initialize message board with some default topics.
Run this after the database migration to create initial topics for testing.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_async_session_context, User
from app.services.message_service import MessageService
from app.schemas.messages import MessageTopicCreate
from sqlalchemy import select


async def init_topics():
    """Create default message topics for all users."""
    
    default_topics = [
        MessageTopicCreate(
            name="General Discussion",
            icon="forum",
            description="General conversations about research and papers"
        ),
        MessageTopicCreate(
            name="Questions",
            icon="help",
            description="Ask questions and get help from the community"
        ),
        MessageTopicCreate(
            name="Paper Recommendations",
            icon="library_books",
            description="Share and discuss interesting papers"
        ),
        MessageTopicCreate(
            name="Research Collaboration",
            icon="group",
            description="Find collaborators and discuss research projects"
        ),
    ]
    
    async with get_async_session_context() as session:
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("No users found in the database. Please create a user first.")
            return
        
        print(f"Found {len(users)} users. Creating topics...")
        
        message_service = MessageService(session)
        
        for user in users:
            print(f"\nCreating topics for user: {user.email}")
            
            for topic_data in default_topics:
                try:
                    topic = await message_service.create_topic(
                        str(user.id), topic_data
                    )
                    print(f"  ✓ Created: {topic.name}")
                except Exception as e:
                    print(f"  ✗ Failed to create {topic_data.name}: {e}")
        
        print("\n✓ Done! Topics initialized successfully.")


if __name__ == "__main__":
    asyncio.run(init_topics())
