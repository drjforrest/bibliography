import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import fitz  # PyMuPDF

from app.config import config

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Service for generating and managing PDF thumbnails."""

    def __init__(self, storage_root: Optional[str] = None, thumbnail_root: Optional[str] = None):
        """
        Initialize the thumbnail generator.

        Args:
            storage_root: Root directory for PDF storage. If None, uses config value.
            thumbnail_root: Root directory for thumbnail storage. If None, uses storage_root/thumbnails.
        """
        self.storage_root = Path(storage_root or getattr(config, 'PDF_STORAGE_ROOT', './data/pdfs'))
        self.thumbnail_root = Path(thumbnail_root or (self.storage_root.parent / 'thumbnails'))
        self.thumbnail_root.mkdir(parents=True, exist_ok=True)

        # Default thumbnail settings
        self.thumbnail_size = (300, 400)  # Width x Height for book-like aspect ratio
        self.thumbnail_quality = 85
        self.thumbnail_format = 'JPEG'

    def generate_thumbnail(self, pdf_path: str, paper_id: int, force_regenerate: bool = False) -> Optional[str]:
        """
        Generate a thumbnail from the first page of a PDF.

        Args:
            pdf_path: Relative or absolute path to the PDF file
            paper_id: Paper ID for organizing thumbnails
            force_regenerate: If True, regenerate even if thumbnail exists

        Returns:
            Relative path to the generated thumbnail, or None if generation failed
        """
        try:
            # Convert relative path to absolute if needed
            if not os.path.isabs(pdf_path):
                absolute_pdf_path = self.storage_root / pdf_path
            else:
                absolute_pdf_path = Path(pdf_path)

            if not absolute_pdf_path.exists():
                logger.error(f"PDF file not found: {absolute_pdf_path}")
                return None

            # Create thumbnail path: thumbnails/YYYY/MM/paper_id.jpg
            # Match the PDF storage structure for consistency
            thumbnail_filename = f"{paper_id}.jpg"

            # Get year/month from PDF path if it follows the storage structure
            parts = Path(pdf_path).parts
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                year_dir = self.thumbnail_root / parts[0]
                month_dir = year_dir / parts[1]
            else:
                # Fallback to year/month based on current date
                from datetime import datetime
                now = datetime.now()
                year_dir = self.thumbnail_root / str(now.year)
                month_dir = year_dir / f"{now.month:02d}"

            month_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = month_dir / thumbnail_filename

            # Check if thumbnail already exists
            if thumbnail_path.exists() and not force_regenerate:
                logger.debug(f"Thumbnail already exists: {thumbnail_path}")
                return str(thumbnail_path.relative_to(self.thumbnail_root))

            # Open PDF and render first page
            doc = fitz.open(str(absolute_pdf_path))

            if len(doc) == 0:
                logger.error(f"PDF has no pages: {absolute_pdf_path}")
                doc.close()
                return None

            # Get first page
            page = doc[0]

            # Calculate zoom to match desired thumbnail width
            # PyMuPDF uses 72 DPI by default, we want higher quality
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Resize to thumbnail size while maintaining aspect ratio
            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

            # Create a canvas with exact thumbnail dimensions (for consistent sizing)
            canvas = Image.new('RGB', self.thumbnail_size, (255, 255, 255))

            # Paste the resized image centered on the canvas
            offset = ((self.thumbnail_size[0] - img.width) // 2,
                     (self.thumbnail_size[1] - img.height) // 2)
            canvas.paste(img, offset)

            # Save thumbnail
            canvas.save(
                thumbnail_path,
                self.thumbnail_format,
                quality=self.thumbnail_quality,
                optimize=True
            )

            doc.close()

            logger.info(f"Generated thumbnail for paper {paper_id}: {thumbnail_path}")

            # Return relative path from thumbnail root
            return str(thumbnail_path.relative_to(self.thumbnail_root))

        except Exception as e:
            logger.error(f"Error generating thumbnail for {pdf_path}: {str(e)}")
            return None

    def get_thumbnail_path(self, relative_path: str) -> Path:
        """
        Convert relative thumbnail path to full file system path.

        Args:
            relative_path: Relative path from thumbnail root

        Returns:
            Full path to the thumbnail file
        """
        return self.thumbnail_root / relative_path

    def thumbnail_exists(self, relative_path: str) -> bool:
        """Check if a thumbnail exists in storage."""
        full_path = self.get_thumbnail_path(relative_path)
        return full_path.exists() and full_path.is_file()

    def delete_thumbnail(self, relative_path: str) -> bool:
        """
        Delete a thumbnail from storage.

        Args:
            relative_path: Relative path to the thumbnail

        Returns:
            True if thumbnail was deleted, False if it didn't exist
        """
        full_path = self.get_thumbnail_path(relative_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def get_thumbnail_stats(self) -> dict:
        """Get thumbnail storage statistics."""
        total_size = 0
        total_files = 0

        if self.thumbnail_root.exists():
            for file_path in self.thumbnail_root.rglob("*.jpg"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size

        return {
            "total_thumbnails": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "thumbnail_root": str(self.thumbnail_root)
        }

    def batch_generate_thumbnails(self, papers: list, force_regenerate: bool = False) -> Tuple[int, int]:
        """
        Generate thumbnails for multiple papers.

        Args:
            papers: List of ScientificPaper objects with id and file_path
            force_regenerate: If True, regenerate existing thumbnails

        Returns:
            Tuple of (success_count, failure_count)
        """
        success_count = 0
        failure_count = 0

        for paper in papers:
            if not paper.file_path:
                logger.warning(f"Paper {paper.id} has no file_path, skipping thumbnail generation")
                failure_count += 1
                continue

            result = self.generate_thumbnail(paper.file_path, paper.id, force_regenerate)
            if result:
                success_count += 1
            else:
                failure_count += 1

        logger.info(f"Batch thumbnail generation: {success_count} succeeded, {failure_count} failed")
        return success_count, failure_count
