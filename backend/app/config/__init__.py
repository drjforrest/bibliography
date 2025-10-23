import os
from pathlib import Path
import shutil

from chonkie import AutoEmbeddings, CodeChunker, RecursiveChunker
from dotenv import load_dotenv
from langchain_community.chat_models import ChatLiteLLM
from rerankers import Reranker

# Try to import OpenAI embeddings from the new package
try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    from langchain_community.embeddings import OpenAIEmbeddings


# Get the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_file = BASE_DIR / ".env"
load_dotenv(env_file)


def is_ffmpeg_installed():
    """
    Check if ffmpeg is installed on the current system.
    
    Returns:
        bool: True if ffmpeg is installed, False otherwise.
    """
    return shutil.which("ffmpeg") is not None



class Config:
    # Check if ffmpeg is installed
    if not is_ffmpeg_installed():
        import static_ffmpeg
        # ffmpeg installed on first call to add_paths(), threadsafe.
        static_ffmpeg.add_paths()
        # check if ffmpeg is installed again
        if not is_ffmpeg_installed():
            raise ValueError("FFmpeg is not installed on the system. Please install it to use the Surfsense Podcaster.")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # PDF Storage
    PDF_STORAGE_ROOT = os.getenv("PDF_STORAGE_ROOT", str(BASE_DIR / "data" / "pdfs"))
    WATCHED_FOLDER = os.getenv("WATCHED_FOLDER", str(BASE_DIR / "data" / "watched"))
    
    NEXT_FRONTEND_URL = os.getenv("NEXT_FRONTEND_URL")
    
    
    # AUTH: Google OAuth
    AUTH_TYPE = os.getenv("AUTH_TYPE")
    if AUTH_TYPE == "GOOGLE":
        GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
        
    
    # LONG-CONTEXT LLMS
    LONG_CONTEXT_LLM = os.getenv("LONG_CONTEXT_LLM")
    LONG_CONTEXT_LLM_API_BASE = os.getenv("LONG_CONTEXT_LLM_API_BASE")
    if LONG_CONTEXT_LLM_API_BASE:
        long_context_llm_instance = ChatLiteLLM(model=LONG_CONTEXT_LLM, api_base=LONG_CONTEXT_LLM_API_BASE)
    else:
        long_context_llm_instance = ChatLiteLLM(model=LONG_CONTEXT_LLM)
    
    # FAST LLM
    FAST_LLM = os.getenv("FAST_LLM")
    FAST_LLM_API_BASE = os.getenv("FAST_LLM_API_BASE")
    if FAST_LLM_API_BASE:
        fast_llm_instance = ChatLiteLLM(model=FAST_LLM, api_base=FAST_LLM_API_BASE)
    else:
        fast_llm_instance = ChatLiteLLM(model=FAST_LLM)
        
        
    
    # STRATEGIC LLM
    STRATEGIC_LLM = os.getenv("STRATEGIC_LLM")
    STRATEGIC_LLM_API_BASE = os.getenv("STRATEGIC_LLM_API_BASE")
    if STRATEGIC_LLM_API_BASE:
        strategic_llm_instance = ChatLiteLLM(model=STRATEGIC_LLM, api_base=STRATEGIC_LLM_API_BASE)
    else:
        strategic_llm_instance = ChatLiteLLM(model=STRATEGIC_LLM)

    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    
    # Configure embedding model based on the type
    if EMBEDDING_MODEL and EMBEDDING_MODEL.startswith("openai://"):
        # Ollama via OpenAI API compatibility
        model_name = EMBEDDING_MODEL.replace("openai://", "")
        try:
            # Try with newer langchain-openai parameters
            embedding_model_instance = OpenAIEmbeddings(
                model=model_name,
                base_url=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"),
                api_key=os.getenv("OPENAI_API_KEY", "ollama")
            )
        except:
            # Fallback to older parameter names
            embedding_model_instance = OpenAIEmbeddings(
                model=model_name,
                openai_api_base=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"),
                openai_api_key=os.getenv("OPENAI_API_KEY", "ollama")
            )
        
        # Set dimension manually for known models
        if "nomic" in model_name:
            embedding_model_instance.dimension = 768
        else:
            embedding_model_instance.dimension = 1536  # Default OpenAI dimension
    else:
        # Use Chonkie AutoEmbeddings for other models
        embedding_model_instance = AutoEmbeddings.get_embeddings(EMBEDDING_MODEL)
    
    # Configure chunkers
    chunk_size = getattr(embedding_model_instance, 'dimension', 512)
    # Use a reasonable chunk size (not the embedding dimension)
    chunker_instance = RecursiveChunker(chunk_size=512)
    code_chunker_instance = CodeChunker(chunk_size=512)
    
    # Reranker's Configuration | Pinecode, Cohere etc. Read more at https://github.com/AnswerDotAI/rerankers?tab=readme-ov-file#usage
    RERANKERS_MODEL_NAME = os.getenv("RERANKERS_MODEL_NAME")
    RERANKERS_MODEL_TYPE = os.getenv("RERANKERS_MODEL_TYPE")
    reranker_instance = Reranker(
        model_name=RERANKERS_MODEL_NAME,
        model_type=RERANKERS_MODEL_TYPE,
    )
    
    # OAuth JWT
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    # Unstructured API Key
    UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")
    
    # Firecrawl API Key
    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", None) 
    
    # Litellm TTS Configuration
    TTS_SERVICE = os.getenv("TTS_SERVICE")
    TTS_SERVICE_API_BASE = os.getenv("TTS_SERVICE_API_BASE")
    
    # Litellm STT Configuration
    STT_SERVICE = os.getenv("STT_SERVICE")
    STT_SERVICE_API_BASE = os.getenv("STT_SERVICE_API_BASE")
    
    
    # Validation Checks
    # Check embedding dimension
    if hasattr(embedding_model_instance, 'dimension') and embedding_model_instance.dimension > 2000:
        raise ValueError(
            f"Embedding dimension for Model: {EMBEDDING_MODEL} "
            f"has {embedding_model_instance.dimension} dimensions, which "
            f"exceeds the maximum of 2000 allowed by PGVector."
        )


    @classmethod
    def get_settings(cls):
        """Get all settings as a dictionary."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }


# Create a config instance
config = Config()
