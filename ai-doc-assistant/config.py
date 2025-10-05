"""Configuration settings for the AI Document Assistant."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
INDEX_DIR = DATA_DIR / "index"
IMAGES_DIR = DATA_DIR / "images"
WATCH_DIR = DATA_DIR / "watch"
PROCESSED_DIR = DATA_DIR / "processed"

# Database settings
DATABASE_PATH = BASE_DIR / "history.db"

# Model settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "mistral"
LLM_BASE_URL = "http://localhost:11434"  # Default Ollama URL
CLIP_MODEL = "openai/clip-vit-base-patch32"

# Text processing settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Vector store settings
VECTOR_STORE_TYPE = "faiss"
INDEX_TYPE = "IndexFlatL2"

# API settings
API_HOST = "127.0.0.1"
API_PORT = 8000

# UI settings
UI_HOST = "127.0.0.1"
UI_PORT = 7860

# Logging settings
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "logs" / "app.log"

# Watch folder settings
WATCH_FOLDER_ENABLED = True
WATCH_FOLDER_AUTO_PROCESS = True
WATCH_FOLDER_MOVE_PROCESSED = True
WATCH_FOLDER_PATTERNS = ["*.pdf", "*.PDF"]
WATCH_FOLDER_RECURSIVE = False


# Create necessary directories
def create_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        DATA_DIR,
        DOCS_DIR,
        INDEX_DIR,
        IMAGES_DIR,
        WATCH_DIR,
        PROCESSED_DIR,
        BASE_DIR / "logs",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Environment variable overrides
def load_env_overrides():
    """Load configuration overrides from environment variables."""
    global LLM_MODEL, LLM_BASE_URL, API_HOST, API_PORT, UI_HOST, UI_PORT

    LLM_MODEL = os.getenv("LLM_MODEL", LLM_MODEL)
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", LLM_BASE_URL)
    API_HOST = os.getenv("API_HOST", API_HOST)
    API_PORT = int(os.getenv("API_PORT", API_PORT))
    UI_HOST = os.getenv("UI_HOST", UI_HOST)
    UI_PORT = int(os.getenv("UI_PORT", UI_PORT))


# Initialize configuration
def init_config():
    """Initialize configuration and create necessary directories."""
    load_env_overrides()
    create_directories()


if __name__ == "__main__":
    init_config()
    print("Configuration initialized successfully!")
    print(f"Base directory: {BASE_DIR}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Database path: {DATABASE_PATH}")
