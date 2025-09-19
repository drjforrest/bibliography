import asyncio
import logging
import os
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class PDFFileHandler(FileSystemEventHandler):
    """Handler for PDF file system events."""
    
    def __init__(self, process_callback: Callable[[str], None]):
        """
        Initialize the handler.
        
        Args:
            process_callback: Async callback function to process new PDF files
        """
        self.process_callback = process_callback
        self.processing_files = set()  # Track files currently being processed
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self._is_pdf_file(file_path) and file_path not in self.processing_files:
            logger.info(f"New PDF detected: {file_path}")
            # Add small delay to ensure file is fully written
            asyncio.create_task(self._process_after_delay(file_path))
    
    def on_moved(self, event):
        """Handle file move events (like downloads completing)."""
        if event.is_directory:
            return
        
        dest_path = event.dest_path
        if self._is_pdf_file(dest_path) and dest_path not in self.processing_files:
            logger.info(f"PDF moved to watched folder: {dest_path}")
            asyncio.create_task(self._process_after_delay(dest_path))
    
    async def _process_after_delay(self, file_path: str, delay: float = 2.0):
        """
        Process file after a delay to ensure it's fully written.
        
        Args:
            file_path: Path to the PDF file
            delay: Delay in seconds before processing
        """
        await asyncio.sleep(delay)
        
        # Check if file still exists and is stable (not being written to)
        if not os.path.exists(file_path):
            logger.warning(f"File no longer exists: {file_path}")
            return
        
        # Check file stability by comparing size after a short wait
        try:
            size1 = os.path.getsize(file_path)
            await asyncio.sleep(0.5)
            size2 = os.path.getsize(file_path)
            
            if size1 != size2:
                logger.info(f"File still being written, delaying processing: {file_path}")
                await asyncio.sleep(2.0)  # Wait longer and try again
                await self._process_after_delay(file_path, 0)
                return
            
            # File appears stable, process it
            self.processing_files.add(file_path)
            try:
                await self.process_callback(file_path)
                logger.info(f"Successfully processed: {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
            finally:
                self.processing_files.discard(file_path)
                
        except Exception as e:
            logger.error(f"Error checking file stability for {file_path}: {str(e)}")
    
    def _is_pdf_file(self, file_path: str) -> bool:
        """Check if file is a PDF."""
        return file_path.lower().endswith('.pdf')


class FolderWatcherService:
    """Service for watching a folder and automatically processing new PDF files."""
    
    def __init__(self, watched_folder: str, process_callback: Callable[[str], None]):
        """
        Initialize the folder watcher.
        
        Args:
            watched_folder: Path to folder to watch
            process_callback: Async callback function to process new PDF files
        """
        self.watched_folder = Path(watched_folder)
        self.process_callback = process_callback
        self.observer = None
        self.is_running = False
        
        # Ensure watched folder exists
        self.watched_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Watching folder: {self.watched_folder}")
    
    def start(self):
        """Start watching the folder."""
        if self.is_running:
            logger.warning("Folder watcher is already running")
            return
        
        self.observer = Observer()
        event_handler = PDFFileHandler(self.process_callback)
        
        self.observer.schedule(
            event_handler,
            str(self.watched_folder),
            recursive=False  # Only watch the main folder, not subdirectories
        )
        
        self.observer.start()
        self.is_running = True
        logger.info(f"Started watching folder: {self.watched_folder}")
        
        # Process any existing PDF files in the folder
        asyncio.create_task(self._process_existing_files())
    
    def stop(self):
        """Stop watching the folder."""
        if not self.is_running or not self.observer:
            return
        
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        logger.info("Stopped folder watcher")
    
    async def _process_existing_files(self):
        """Process any PDF files that are already in the watched folder."""
        try:
            existing_pdfs = list(self.watched_folder.glob("*.pdf"))
            if existing_pdfs:
                logger.info(f"Found {len(existing_pdfs)} existing PDF files to process")
                
                for pdf_path in existing_pdfs:
                    try:
                        await self.process_callback(str(pdf_path))
                        logger.info(f"Processed existing file: {pdf_path}")
                    except Exception as e:
                        logger.error(f"Error processing existing file {pdf_path}: {str(e)}")
            else:
                logger.info("No existing PDF files found in watched folder")
                
        except Exception as e:
            logger.error(f"Error processing existing files: {str(e)}")
    
    def get_status(self) -> dict:
        """Get the current status of the folder watcher."""
        return {
            "is_running": self.is_running,
            "watched_folder": str(self.watched_folder),
            "folder_exists": self.watched_folder.exists(),
            "pdf_count": len(list(self.watched_folder.glob("*.pdf"))) if self.watched_folder.exists() else 0
        }


class FolderWatcherManager:
    """Manager for the folder watcher service (singleton)."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.watcher = None
        return cls._instance
    
    def initialize(self, watched_folder: str, process_callback: Callable[[str], None]):
        """Initialize the folder watcher."""
        if self.watcher:
            self.watcher.stop()
        
        self.watcher = FolderWatcherService(watched_folder, process_callback)
    
    def start(self):
        """Start the folder watcher."""
        if self.watcher:
            self.watcher.start()
    
    def stop(self):
        """Stop the folder watcher."""
        if self.watcher:
            self.watcher.stop()
    
    def get_status(self) -> Optional[dict]:
        """Get watcher status."""
        return self.watcher.get_status() if self.watcher else None


# Global instance
folder_watcher_manager = FolderWatcherManager()