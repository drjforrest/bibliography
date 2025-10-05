"""Setup script for the AI Document Assistant."""

import sqlite3
import sys
from loguru import logger

import config


def setup_database():
    """Initialize the SQLite database with required tables."""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        # Create the log table for storing interactions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                q TEXT NOT NULL,
                a TEXT NOT NULL,
                source_docs TEXT,
                metadata TEXT
            )
        """
        )

        # Create index for faster queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp ON log(timestamp)
        """
        )

        conn.commit()
        conn.close()

        logger.info(f"Database initialized successfully at {config.DATABASE_PATH}")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def setup_vector_stores():
    """Initialize vector store directories and metadata files."""
    try:
        # Create metadata file for text embeddings
        text_metadata_file = config.INDEX_DIR / "text_metadata.json"
        if not text_metadata_file.exists():
            import json

            metadata = {
                "embedding_model": config.EMBEDDING_MODEL,
                "chunk_size": config.CHUNK_SIZE,
                "chunk_overlap": config.CHUNK_OVERLAP,
                "created_at": None,
                "total_documents": 0,
                "total_chunks": 0,
            }
            with open(text_metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

        # Create metadata file for image embeddings
        image_metadata_file = config.INDEX_DIR / "image_metadata.json"
        if not image_metadata_file.exists():
            import json

            metadata = {
                "clip_model": config.CLIP_MODEL,
                "created_at": None,
                "total_images": 0,
            }
            with open(image_metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

        logger.info("Vector store directories and metadata initialized")
        return True

    except Exception as e:
        logger.error(f"Failed to setup vector stores: {e}")
        return False


def setup_logging():
    """Configure logging for the application."""
    try:
        # Configure loguru
        logger.remove()  # Remove default handler

        # Add file handler
        logger.add(
            config.LOG_FILE,
            rotation="10 MB",
            retention="30 days",
            level=config.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        )

        # Add console handler
        logger.add(
            sys.stderr,
            level=config.LOG_LEVEL,
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {message}",
        )

        logger.info("Logging configured successfully")
        return True

    except Exception as e:
        print(f"Failed to setup logging: {e}")
        return False


def main():
    """Run the complete setup process."""
    print("🚀 Setting up AI Document Assistant...")

    success_count = 0
    total_steps = 4

    # Step 1: Initialize configuration
    print("1. Initializing configuration...")
    try:
        config.init_config()
        print("✅ Configuration initialized")
        success_count += 1
    except Exception as e:
        print(f"❌ Configuration failed: {e}")

    # Step 2: Setup logging
    print("2. Setting up logging...")
    if setup_logging():
        print("✅ Logging configured")
        success_count += 1
    else:
        print("❌ Logging setup failed")

    # Step 3: Setup database
    print("3. Initializing database...")
    if setup_database():
        print("✅ Database initialized")
        success_count += 1
    else:
        print("❌ Database setup failed")

    # Step 4: Setup vector stores
    print("4. Setting up vector stores...")
    if setup_vector_stores():
        print("✅ Vector stores configured")
        success_count += 1
    else:
        print("❌ Vector store setup failed")

    # Summary
    print(f"\n📊 Setup completed: {success_count}/{total_steps} steps successful")

    if success_count == total_steps:
        print("🎉 All setup completed successfully!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Make sure Ollama is running with the mistral model")
        print("3. Run the application: python main.py")
        return True
    else:
        print("⚠️  Some setup steps failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    main()
