"""
Watch folder service for automatically processing PDF documents.
"""

import time
import shutil
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from loguru import logger
import fnmatch

import config
from ingest.extract_text import extract_text
from process.chunk_text import chunk_text
from process.embed_chunks import embed_chunks
from index.vector_store_text import save_vector_store


class PDFWatchHandler(FileSystemEventHandler):
    """File system event handler for PDF files."""

    def __init__(self, processor_callback: Callable[[str], bool]):
        self.processor_callback = processor_callback
        self.processing_files = set()  # type: Set[str]  # Track files currently being processed
        super().__init__()

    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed."""
        file_path_obj = Path(file_path)

        # Check if file matches our patterns
        for pattern in config.WATCH_FOLDER_PATTERNS:
            if fnmatch.fnmatch(file_path_obj.name, pattern):
                return True

        return False

    def _is_file_ready(self, file_path: str, max_wait: int = 30) -> bool:
        """Check if file is ready for processing (not being written to)."""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return False

        # Wait for file to stabilize (no size changes)
        previous_size = -1
        stable_count = 0

        for _ in range(max_wait):
            try:
                current_size = file_path_obj.stat().st_size

                if current_size == previous_size and current_size > 0:
                    stable_count += 1
                    if stable_count >= 3:  # File size stable for 3 checks
                        return True
                else:
                    stable_count = 0

                previous_size = current_size
                time.sleep(1)

            except (OSError, FileNotFoundError):
                return False

        return False

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        self._handle_file_event(str(event.src_path), "created")

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events."""
        if event.is_directory:
            return

        self._handle_file_event(str(event.dest_path), "moved")

    def _handle_file_event(self, file_path: str, event_type: str) -> None:
        """Handle a file event."""
        if not self._should_process_file(file_path):
            return

        file_path = str(Path(file_path).resolve())

        # Avoid processing the same file multiple times
        if file_path in self.processing_files:
            logger.debug(f"File already being processed: {file_path}")
            return

        logger.info(f"New PDF detected ({event_type}): {file_path}")

        # Process in a separate thread to avoid blocking the observer
        thread = threading.Thread(
            target=self._process_file_async, args=(file_path,), daemon=True
        )
        thread.start()

    def _process_file_async(self, file_path: str) -> None:
        """Process file asynchronously."""
        try:
            self.processing_files.add(file_path)

            # Wait for file to be ready
            if not self._is_file_ready(file_path):
                logger.warning(f"File not ready for processing: {file_path}")
                return

            # Process the file
            success = self.processor_callback(file_path)

            if success and config.WATCH_FOLDER_MOVE_PROCESSED:
                self._move_processed_file(file_path)

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

        finally:
            self.processing_files.discard(file_path)

    def _move_processed_file(self, file_path: str) -> None:
        """Move processed file to the processed directory."""
        try:
            source_path = Path(file_path)
            dest_path = config.PROCESSED_DIR / source_path.name

            # Handle filename conflicts
            counter = 1
            original_dest = dest_path
            while dest_path.exists():
                stem = original_dest.stem
                suffix = original_dest.suffix
                dest_path = config.PROCESSED_DIR / f"{stem}_{counter}{suffix}"
                counter += 1

            shutil.move(str(source_path), str(dest_path))
            logger.info(f"Moved processed file: {source_path} -> {dest_path}")

        except Exception as e:
            logger.error(f"Failed to move processed file {file_path}: {e}")


class WatchFolderService:
    """Service for monitoring and processing PDF files in a watch folder."""

    def __init__(self):
        self.observer = None  # type: Optional[Observer]
        self.is_running = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start the watch folder service."""
        with self._lock:
            if self.is_running:
                logger.warning("Watch folder service is already running")
                return True

            try:
                # Ensure watch directory exists
                config.WATCH_DIR.mkdir(parents=True, exist_ok=True)
                config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

                # Create handler
                handler = PDFWatchHandler(processor_callback=self._process_document)

                # Create and configure observer
                self.observer = Observer()
                assert self.observer is not None
                self.observer.schedule(
                    handler,
                    str(config.WATCH_DIR),
                    recursive=config.WATCH_FOLDER_RECURSIVE,
                )

                # Start observer
                self.observer.start()
                self.is_running = True

                logger.info(f"Watch folder service started: {config.WATCH_DIR}")
                logger.info(f"Monitoring patterns: {config.WATCH_FOLDER_PATTERNS}")
                logger.info(f"Recursive: {config.WATCH_FOLDER_RECURSIVE}")
                logger.info(
                    f"Auto-move processed: {config.WATCH_FOLDER_MOVE_PROCESSED}"
                )

                return True

            except Exception as e:
                logger.error(f"Failed to start watch folder service: {e}")
                return False

    def stop(self) -> bool:
        """Stop the watch folder service."""
        with self._lock:
            if not self.is_running:
                logger.warning("Watch folder service is not running")
                return True

            try:
                if self.observer:
                    self.observer.stop()
                    self.observer.join(timeout=5.0)  # Wait up to 5 seconds

                self.observer = None
                self.is_running = False

                logger.info("Watch folder service stopped")
                return True

            except Exception as e:
                logger.error(f"Failed to stop watch folder service: {e}")
                return False

    def is_active(self) -> bool:
        """Check if the service is running."""
        return self.is_running

    def get_status(self) -> Dict[str, Any]:
        """Get service status information."""
        return {
            "active": self.is_running,
            "watch_directory": str(config.WATCH_DIR),
            "processed_directory": str(config.PROCESSED_DIR),
            "patterns": config.WATCH_FOLDER_PATTERNS,
            "recursive": config.WATCH_FOLDER_RECURSIVE,
            "auto_move_processed": config.WATCH_FOLDER_MOVE_PROCESSED,
        }

    def _process_document(self, file_path: str) -> bool:
        """Process a PDF document through the full pipeline."""
        try:
            logger.info(f"Processing document: {file_path}")

            # Extract text
            logger.debug("Extracting text...")
            pages = extract_text(file_path)

            if not pages:
                logger.warning(f"No text extracted from: {file_path}")
                return False

            # Chunk text
            logger.debug("Chunking text...")
            all_chunks = []
            all_metadata = []

            for page in pages:
                chunks = chunk_text(
                    page["text"], config.CHUNK_SIZE, config.CHUNK_OVERLAP
                )
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        all_chunks.append(chunk)
                        all_metadata.append(
                            {
                                "file": page["file"],
                                "page": page["page"],
                                "chunk_id": i,
                                "processing_method": "watch_folder",
                            }
                        )

            if not all_chunks:
                logger.warning(f"No valid chunks created from: {file_path}")
                return False

            # Generate embeddings
            logger.debug("Generating embeddings...")
            embeddings = embed_chunks(all_chunks)

            # Save to vector store
            logger.debug("Saving to vector store...")
            success = save_vector_store(embeddings, all_chunks, all_metadata)

            if success:
                logger.info(
                    f"Successfully processed {file_path}: {len(all_chunks)} chunks from {len(pages)} pages"
                )

                # Reload QA system to pick up new documents
                try:
                    from backend.qa_chain import get_qa_system

                    qa_system = get_qa_system()
                    qa_system._load_vector_store()
                    logger.debug("QA system reloaded with new documents")
                except Exception as e:
                    logger.warning(f"Failed to reload QA system: {e}")

                return True
            else:
                logger.error(f"Failed to save vector store for: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return False

    def process_existing_files(self) -> Dict[str, Any]:
        """Process any existing PDF files in the watch directory."""
        results = {"processed": 0, "failed": 0, "skipped": 0, "files": []}  # type: Dict[str, Any]

        try:
            watch_path = Path(config.WATCH_DIR)

            if not watch_path.exists():
                logger.warning("Watch directory does not exist")
                return results

            # Find all matching files
            pdf_files = []
            for pattern in config.WATCH_FOLDER_PATTERNS:
                if config.WATCH_FOLDER_RECURSIVE:
                    pdf_files.extend(watch_path.rglob(pattern))
                else:
                    pdf_files.extend(watch_path.glob(pattern))

            logger.info(f"Found {len(pdf_files)} existing PDF files to process")

            for pdf_file in pdf_files:
                file_path = str(pdf_file.resolve())
                file_result = {"file": file_path, "status": "unknown"}

                try:
                    if self._process_document(file_path):
                        file_result["status"] = "success"
                        results["processed"] += 1

                        # Move processed file if configured
                        if config.WATCH_FOLDER_MOVE_PROCESSED:
                            PDFWatchHandler(
                                self._process_document
                            )._move_processed_file(file_path)
                    else:
                        file_result["status"] = "failed"
                        results["failed"] += 1

                except Exception as e:
                    file_result["status"] = f"error: {str(e)}"
                    results["failed"] += 1
                    logger.error(f"Error processing existing file {file_path}: {e}")

                results["files"].append(file_result)

            logger.info(
                f"Existing file processing complete: {results['processed']} success, {results['failed']} failed"
            )

        except Exception as e:
            logger.error(f"Error processing existing files: {e}")

        return results


# Global service instance
_watch_service: Optional[WatchFolderService] = None


def get_watch_service() -> WatchFolderService:
    """Get or create the global watch service instance."""
    global _watch_service
    if _watch_service is None:
        _watch_service = WatchFolderService()
    return _watch_service
