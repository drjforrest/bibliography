"""Document ingestion module."""

from .extract_text import extract_text
from .extract_images import extract_images

__all__ = ["extract_text", "extract_images"]
