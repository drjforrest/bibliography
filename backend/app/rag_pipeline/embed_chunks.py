"""
Legacy RAG pipeline embedding module.

NOTE: This module requires sentence-transformers, which is now an optional dependency.
To use this module, install torch dependencies: uv pip install -e ".[torch-deps]"
"""

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

model = None
if SENTENCE_TRANSFORMERS_AVAILABLE:
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        model = None


def embed_chunks(chunks):
    """
    Embed text chunks using sentence-transformers.
    
    Requires torch dependencies: uv pip install -e ".[torch-deps]"
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE or model is None:
        raise ImportError(
            "sentence-transformers is required for this function. "
            "Install with: uv pip install -e '.[torch-deps]'"
        )
    return model.encode(chunks)
