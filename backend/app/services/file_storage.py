import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple

from app.config import config


class FileStorageService:
    """Service for managing PDF file storage with UUID-based paths."""
    
    def __init__(self, storage_root: Optional[str] = None):
        """
        Initialize the file storage service.
        
        Args:
            storage_root: Root directory for file storage. If None, uses config value.
        """
        self.storage_root = Path(storage_root or getattr(config, 'PDF_STORAGE_ROOT', './data/pdfs'))
        self.storage_root.mkdir(parents=True, exist_ok=True)
    
    def store_pdf(self, source_path: str, paper_id: Optional[int] = None) -> Tuple[str, str]:
        """
        Store a PDF file in the managed storage with UUID-based path.
        
        Args:
            source_path: Path to the source PDF file
            paper_id: Optional paper ID for subdirectory organization
            
        Returns:
            Tuple of (stored_file_path, file_uuid)
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Generate UUID for the file
        file_uuid = str(uuid.uuid4())
        
        # Create subdirectory structure: storage_root/year/month/uuid.pdf
        # This helps with file system performance and organization
        from datetime import datetime
        now = datetime.now()
        year_dir = self.storage_root / str(now.year)
        month_dir = year_dir / f"{now.month:02d}"
        month_dir.mkdir(parents=True, exist_ok=True)
        
        # Store with UUID filename
        stored_filename = f"{file_uuid}.pdf"
        stored_path = month_dir / stored_filename
        
        # Copy the file to storage location
        shutil.copy2(source_path, stored_path)
        
        # Return relative path from storage root for database storage
        relative_path = str(stored_path.relative_to(self.storage_root))
        
        return relative_path, file_uuid
    
    def get_full_path(self, relative_path: str) -> Path:
        """
        Convert relative storage path to full file system path.
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            Full path to the file
        """
        return self.storage_root / relative_path
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in storage."""
        full_path = self.get_full_path(relative_path)
        return full_path.exists() and full_path.is_file()
    
    def get_file_size(self, relative_path: str) -> int:
        """Get file size in bytes."""
        full_path = self.get_full_path(relative_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return full_path.stat().st_size
    
    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            relative_path: Relative path to the file
            
        Returns:
            True if file was deleted, False if it didn't exist
        """
        full_path = self.get_full_path(relative_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    def move_temp_file(self, temp_path: str) -> Tuple[str, str]:
        """
        Move a temporary uploaded file to permanent storage.
        
        Args:
            temp_path: Path to temporary file
            
        Returns:
            Tuple of (stored_relative_path, file_uuid)
        """
        return self.store_pdf(temp_path)
    
    def create_watched_folder(self, folder_name: str = "watched") -> Path:
        """
        Create a watched folder for automatic PDF processing.
        
        Args:
            folder_name: Name of the watched folder
            
        Returns:
            Path to the watched folder
        """
        watched_folder = self.storage_root.parent / folder_name
        watched_folder.mkdir(parents=True, exist_ok=True)
        return watched_folder
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        total_size = 0
        total_files = 0
        
        if self.storage_root.exists():
            for file_path in self.storage_root.rglob("*.pdf"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_root": str(self.storage_root)
        }