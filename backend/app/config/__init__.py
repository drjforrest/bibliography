import logging
import os
import shutil
import warnings
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

# Try to import ChatLiteLLM from the new package first
try:
    from langchain_litellm import ChatLiteLLM
except ImportError:
    # Suppress deprecation warning for old import
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        from langchain_community.chat_models import ChatLiteLLM

# Try to import OpenAI embeddings from the new package
try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    from langchain_community.embeddings import OpenAIEmbeddings

# Use LangChain text splitters instead of chonkie (which requires torch/sentence-transformers)
# LangChain splitters are lightweight and work on macOS Intel without heavy dependencies
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_TEXT_SPLITTER_AVAILABLE = True
except ImportError:
    try:
        from langchain_community.text_splitter import RecursiveCharacterTextSplitter
        LANGCHAIN_TEXT_SPLITTER_AVAILABLE = True
    except ImportError:
        RecursiveCharacterTextSplitter = None
        LANGCHAIN_TEXT_SPLITTER_AVAILABLE = False

# Optional imports - rerankers may not be available on all platforms
try:
    from rerankers import Reranker

    RERANKERS_AVAILABLE = True
except ImportError:
    Reranker = None
    RERANKERS_AVAILABLE = False


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
            raise ValueError(
                "FFmpeg is not installed on the system. Please install it to use the Surfsense Podcaster."
            )

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
        long_context_llm_instance = ChatLiteLLM(
            model=LONG_CONTEXT_LLM, api_base=LONG_CONTEXT_LLM_API_BASE
        )
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
        strategic_llm_instance = ChatLiteLLM(
            model=STRATEGIC_LLM, api_base=STRATEGIC_LLM_API_BASE
        )
    else:
        strategic_llm_instance = ChatLiteLLM(model=STRATEGIC_LLM)

    # Embedding Configuration
    # Default to OpenAI-compatible embedding model (nomic-embed-text via LMStudio/Ollama)
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai://nomic-embed-text")

    # Configure embedding model based on the type
    embedding_model_instance = None
    embedding_dimension = 1536  # Default dimension

    if EMBEDDING_MODEL:
        # Normalize common typos/variations (penai:// -> openai://)
        normalized_model = EMBEDDING_MODEL.strip()
        if normalized_model.startswith("penai://"):
            normalized_model = "openai://" + normalized_model[7:]
            logger.warning(
                f"Fixed typo in EMBEDDING_MODEL: '{EMBEDDING_MODEL}' -> '{normalized_model}'"
            )
            EMBEDDING_MODEL = normalized_model
        
        if EMBEDDING_MODEL.startswith("openai://"):
            # Ollama via OpenAI API compatibility
            model_name = EMBEDDING_MODEL.replace("openai://", "")
            try:
                # Try with newer langchain-openai parameters
                embedding_model_instance = OpenAIEmbeddings(
                    model=model_name,
                    base_url=os.getenv(
                        "OPENAI_API_BASE", "http://192.168.1.81:1234/v1"
                    ),
                    api_key=os.getenv("OPENAI_API_KEY", "ollama"),
                )
            except:
                # Fallback to older parameter names
                embedding_model_instance = OpenAIEmbeddings(
                    model=model_name,
                    openai_api_base=os.getenv(
                        "OPENAI_API_BASE", "http://192.168.1.81:1234/v1"
                    ),
                    openai_api_key=os.getenv("OPENAI_API_KEY", "ollama"),
                )

            # Store dimension separately (OpenAIEmbeddings doesn't expose this as a settable attribute)
            if "nomic" in model_name:
                embedding_dimension = 768
            else:
                embedding_dimension = 1536  # Default OpenAI dimension
        else:
            # For non-OpenAI models, suggest using OpenAI-style embeddings
            import warnings

            warnings.warn(
                f"EMBEDDING_MODEL '{EMBEDDING_MODEL}' is not an OpenAI-style model. "
                "Please set EMBEDDING_MODEL to use OpenAI-style embeddings (e.g., 'openai://nomic-embed-text'). "
                "Embedding operations will fail until this is fixed.",
                UserWarning,
            )
            # Try to use a default OpenAI-style model as fallback
            try:
                model_name = "nomic-embed-text"  # Default fallback
                embedding_model_instance = OpenAIEmbeddings(
                    model=model_name,
                    base_url=os.getenv(
                        "OPENAI_API_BASE", "http://192.168.1.81:1234/v1"
                    ),
                    api_key=os.getenv("OPENAI_API_KEY", "ollama"),
                )
                embedding_dimension = 768
                warnings.warn(
                    f"Using fallback embedding model: openai://{model_name}. "
                    f"Original model '{EMBEDDING_MODEL}' is not supported.",
                    UserWarning,
                )
            except Exception as e:
                warnings.warn(
                    f"Could not initialize fallback embedding model: {e}. "
                    "Embedding operations will fail. Please fix EMBEDDING_MODEL in your .env file.",
                    UserWarning,
                )
                # Set to None explicitly so code can check and fail gracefully
                embedding_model_instance = None
                embedding_dimension = 768  # Default dimension even if model fails

    # Note: embedding_dimension is stored as a separate config variable
    # Use config.embedding_dimension instead of config.embedding_model_instance.dimension
    # The embedding_model_instance (OpenAIEmbeddings) doesn't expose dimension as a settable attribute

    # Configure chunkers using LangChain text splitters (no torch/sentence-transformers required)
    # Wrap LangChain splitters to match the expected interface (chunks with .text attribute)
    class ChunkWrapper:
        """Wrapper to make LangChain chunks compatible with chonkie interface."""
        def __init__(self, text):
            self.text = text
            self.content = text  # Also support .content for compatibility
            self.page_content = text  # LangChain compatibility
    
    class LangChainChunkerAdapter:
        """Adapter to make LangChain text splitter work like chonkie chunker."""
        def __init__(self, splitter):
            self.splitter = splitter
        
        def chunk(self, text: str):
            """Split text and return chunks with .text attribute."""
            if not text or not text.strip():
                return []
            
            # Use LangChain splitter to create chunks
            langchain_chunks = self.splitter.split_text(text)
            
            # Wrap each chunk to match chonkie interface
            return [ChunkWrapper(chunk_text) for chunk_text in langchain_chunks if chunk_text.strip()]
    
    # Use LangChain RecursiveCharacterTextSplitter for general text
    if LANGCHAIN_TEXT_SPLITTER_AVAILABLE:
        # General text chunker with recursive character splitting
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunker_instance = LangChainChunkerAdapter(text_splitter)
        
        # Code-aware chunker for GitHub files (use Python as default language)
        # LangChain doesn't have a built-in code splitter, so we use the same splitter
        # but with better separators for code
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", "def ", "class ", "    ", " ", ""]  # Code-aware separators
        )
        code_chunker_instance = LangChainChunkerAdapter(code_splitter)
    else:
        # Fallback simple chunker if LangChain is not available
        class SimpleChunker:
            """Simple chunker that splits text into fixed-size chunks."""

            def __init__(self, chunk_size=512, overlap=100):
                self.chunk_size = chunk_size
                self.overlap = overlap

            def chunk(self, text: str):
                """Split text into overlapping chunks."""
                if not text or not text.strip():
                    return []

                chunks = []
                text_length = len(text)

                # If text is shorter than chunk size, return as single chunk
                if text_length <= self.chunk_size:
                    return [ChunkWrapper(text.strip())]

                start = 0
                while start < text_length:
                    end = min(start + self.chunk_size, text_length)
                    chunk = text[start:end].strip()

                    if chunk:
                        chunks.append(ChunkWrapper(chunk))

                    # Break if we've reached the end
                    if end >= text_length:
                        break

                    # Move start position with overlap
                    start = end - self.overlap

                return chunks

        chunker_instance = SimpleChunker(chunk_size=512, overlap=100)
        code_chunker_instance = SimpleChunker(chunk_size=512, overlap=100)

    # Reranker's Configuration | Pinecode, Cohere etc. Read more at https://github.com/AnswerDotAI/rerankers?tab=readme-ov-file#usage
    RERANKERS_MODEL_NAME = os.getenv("RERANKERS_MODEL_NAME")
    RERANKERS_MODEL_TYPE = os.getenv("RERANKERS_MODEL_TYPE")
    if RERANKERS_AVAILABLE and RERANKERS_MODEL_NAME and RERANKERS_MODEL_TYPE:
        reranker_instance = Reranker(
            model_name=RERANKERS_MODEL_NAME,
            model_type=RERANKERS_MODEL_TYPE,
        )
    else:
        reranker_instance = None

    # OAuth JWT
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Clerk Authentication
    # Note: Clerk exports CLERK_SECRET_KEY, which we use for backend API calls
    CLERK_API_KEY = os.getenv("CLERK_SECRET_KEY")  # Clerk API key for backend

    # Clerk exports NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY for frontend, but backend also needs it
    # Support both CLERK_PUBLISHABLE_KEY (explicit) and NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY (Clerk export)
    CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY") or os.getenv(
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"
    )

    # Webhook signing key (not in Clerk's export, must be set from webhook settings)
    CLERK_WEBHOOK_SIGNING_KEY = os.getenv("CLERK_WEBHOOK_SECRET")  # Webhook signing key

    # Environment-aware defaults for Clerk issuer and JWKS URL
    # Prevents non-production environments from accidentally using production auth
    APP_ENV = os.getenv("APP_ENV", "").lower()
    if APP_ENV == "production":
        # Only allow production defaults in explicit production environment
        _default_clerk_issuer = "https://clerk.counterforce-hero.tech"
        _default_clerk_jwks_url = (
            "https://clerk.counterforce-hero.tech/.well-known/jwks.json"
        )
    else:
        # For dev/staging/other environments, require explicit configuration
        # Use placeholder values that will fail safely if not overridden
        _default_clerk_issuer = None
        _default_clerk_jwks_url = None

    # Clerk exports CLERK_FRONTEND_API_URL, which is the same as CLERK_ISSUER
    # Support both CLERK_ISSUER (explicit) and CLERK_FRONTEND_API_URL (Clerk export)
    CLERK_ISSUER = (
        os.getenv("CLERK_ISSUER")
        or os.getenv("CLERK_FRONTEND_API_URL")
        or _default_clerk_issuer
    )
    # Allow running scripts without Clerk config (only needed for API endpoints)
    if not CLERK_ISSUER:
        CLERK_ISSUER = None
        logger.warning(
            "CLERK_ISSUER not set - Clerk authentication will not work. "
            "This is fine for running scripts, but required for API endpoints."
        )

    CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", _default_clerk_jwks_url)
    if not CLERK_JWKS_URL:
        CLERK_JWKS_URL = None
        logger.warning(
            "CLERK_JWKS_URL not set - Clerk authentication will not work. "
            "This is fine for running scripts, but required for API endpoints."
        )

    # Optional: audience for token verification (None means audience validation is skipped)
    CLERK_AUDIENCE: Optional[str] = os.getenv("CLERK_AUDIENCE") or None

    # Unstructured API Key
    UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")

    # Firecrawl API Key
    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", None)

    # Semantic Scholar API Key (optional, for higher rate limits)
    # Get free at: https://www.semanticscholar.org/product/api
    SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", None)

    # Litellm TTS Configuration
    TTS_SERVICE = os.getenv("TTS_SERVICE")
    TTS_SERVICE_API_BASE = os.getenv("TTS_SERVICE_API_BASE")

    # Litellm STT Configuration
    STT_SERVICE = os.getenv("STT_SERVICE")
    STT_SERVICE_API_BASE = os.getenv("STT_SERVICE_API_BASE")

    # Validation Checks
    # Check embedding dimension
    if embedding_dimension > 2000:
        raise ValueError(
            f"Embedding dimension for Model: {EMBEDDING_MODEL} "
            f"has {embedding_dimension} dimensions, which "
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
