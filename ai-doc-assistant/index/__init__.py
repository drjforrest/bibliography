"""Vector indexing module."""

from .vector_store_text import build_index
from .vector_store_images import embed_image

__all__ = ["build_index", "embed_image"]
