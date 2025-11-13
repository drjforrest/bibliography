import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db import Document, ScientificPaper, DocumentType, User
from app.services.file_storage import FileStorageService
from app.services.folder_watcher import folder_watcher_manager
from app.services.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class PaperManagerService:
    """
    Comprehensive service for managing scientific papers including:
    - PDF processing and metadata extraction
    - File storage with UUID-based paths
    - Database operations
    - Integration with folder watching
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.pdf_processor = PDFProcessor(session)
        self.file_storage = FileStorageService()
    
    async def process_pdf_file(self, file_path: str, user_id: str, search_space_id: int,
                              literature_type: str = "PEER_REVIEWED",
                              move_file: bool = True) -> Optional[Dict]:
        """
        Process a PDF file completely: extract metadata, store file, save to database.

        Args:
            file_path: Path to the PDF file to process
            user_id: ID of the user adding the paper
            search_space_id: ID of the search space to add the paper to
            literature_type: Type of literature (PEER_REVIEWED, GREY_LITERATURE, NEWS)
            move_file: Whether to move the file to managed storage (vs. copy)

        Returns:
            Dictionary with processing results and paper information
        """
        try:
            logger.info(f"Processing PDF: {file_path}")
            
            # Check if file already exists in database (by hash)
            file_hash = self.pdf_processor._calculate_file_hash(file_path)
            existing_paper = await self._get_paper_by_hash(file_hash)
            if existing_paper:
                logger.info(f"File already exists in database: {file_path}")
                return {
                    'status': 'duplicate',
                    'paper_id': existing_paper.id,
                    'message': 'PDF already exists in the database'
                }
            
            # Extract metadata using PDF processor
            extracted_data = await self.pdf_processor.process_pdf(file_path)
            
            if extracted_data.get('processing_status') == 'failed':
                logger.error(f"Failed to process PDF: {file_path}")
                return {
                    'status': 'failed',
                    'error': extracted_data.get('extraction_metadata', {}).get('error', 'Unknown error'),
                    'file_path': file_path
                }
            
            # Store the file in managed storage
            if move_file:
                stored_path, file_uuid = self.file_storage.store_pdf(file_path)
                # Remove original file after successful storage
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.warning(f"Could not remove original file {file_path}: {e}")
            else:
                stored_path, file_uuid = self.file_storage.store_pdf(file_path)
            
            # Create database records
            paper_id = await self._create_paper_records(
                extracted_data=extracted_data,
                stored_path=stored_path,
                file_uuid=file_uuid,
                search_space_id=search_space_id,
                literature_type=literature_type
            )
            
            logger.info(f"Successfully processed PDF: {file_path} -> Paper ID: {paper_id}")
            
            return {
                'status': 'success',
                'paper_id': paper_id,
                'title': extracted_data.get('title'),
                'authors': extracted_data.get('authors'),
                'stored_path': stored_path,
                'extraction_confidence': extracted_data.get('extraction_metadata', {}).get('extraction_confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'file_path': file_path
            }
    
    async def _get_paper_by_hash(self, file_hash: str) -> Optional[ScientificPaper]:
        """Check if a paper with the same file hash already exists."""
        stmt = select(ScientificPaper).where(ScientificPaper.file_hash == file_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _create_paper_records(self, extracted_data: Dict, stored_path: str,
                                   file_uuid: str, search_space_id: int,
                                   literature_type: str = "PEER_REVIEWED") -> int:
        """Create Document and ScientificPaper records in the database."""

        # Create Document record
        document = Document(
            title=extracted_data.get('title', 'Untitled Paper'),
            document_type=DocumentType.SCIENTIFIC_PAPER,
            content=extracted_data.get('full_text', ''),
            document_metadata={
                'file_uuid': file_uuid,
                'extraction_metadata': extracted_data.get('extraction_metadata', {}),
                'original_filename': os.path.basename(extracted_data.get('file_path', ''))
            },
            search_space_id=search_space_id
        )

        self.session.add(document)
        await self.session.flush()  # Get the document ID

        # Create ScientificPaper record
        scientific_paper = ScientificPaper(
            literature_type=literature_type,
            title=extracted_data.get('title'),
            authors=extracted_data.get('authors', []),
            journal=extracted_data.get('journal'),
            volume=extracted_data.get('volume'),
            issue=extracted_data.get('issue'),
            pages=extracted_data.get('pages'),
            publication_year=extracted_data.get('publication_year'),
            doi=extracted_data.get('doi'),
            abstract=extracted_data.get('abstract'),
            keywords=extracted_data.get('keywords', []),
            full_text=extracted_data.get('full_text'),
            file_path=stored_path,
            file_size=extracted_data.get('file_size'),
            file_hash=extracted_data.get('file_hash'),
            references=extracted_data.get('references', []),
            processing_status=extracted_data.get('processing_status', 'completed'),
            extraction_metadata=extracted_data.get('extraction_metadata', {}),
            confidence_score=extracted_data.get('extraction_metadata', {}).get('extraction_confidence', 0.0),
            document_id=document.id
        )

        self.session.add(scientific_paper)
        await self.session.commit()

        return scientific_paper.id
    
    async def get_paper_by_id(self, paper_id: int) -> Optional[ScientificPaper]:
        """Get a scientific paper by ID."""
        stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_papers_by_user(self, user_id: str, search_space_id: Optional[int] = None,
                                literature_type: Optional[str] = None,
                                limit: int = 50, offset: int = 0) -> List[ScientificPaper]:
        """Get papers for a user, optionally filtered by search space and literature type."""
        stmt = select(ScientificPaper).join(Document)

        if search_space_id:
            stmt = stmt.where(Document.search_space_id == search_space_id)

        if literature_type:
            stmt = stmt.where(ScientificPaper.literature_type == literature_type)

        stmt = stmt.limit(limit).offset(offset).order_by(ScientificPaper.created_at.desc())

        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def search_papers(self, query: str, search_space_id: Optional[int] = None,
                           limit: int = 20) -> List[ScientificPaper]:
        """Search papers by title, authors, or abstract."""
        from sqlalchemy import or_, func
        
        stmt = select(ScientificPaper).join(Document)
        
        # Search in title, authors (as text), and abstract
        search_conditions = or_(
            ScientificPaper.title.ilike(f'%{query}%'),
            func.array_to_string(ScientificPaper.authors, ' ').ilike(f'%{query}%'),
            ScientificPaper.abstract.ilike(f'%{query}%'),
            ScientificPaper.journal.ilike(f'%{query}%')
        )
        
        stmt = stmt.where(search_conditions)
        
        if search_space_id:
            stmt = stmt.where(Document.search_space_id == search_space_id)
        
        stmt = stmt.limit(limit).order_by(ScientificPaper.created_at.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def delete_paper(self, paper_id: int) -> bool:
        """Delete a paper and its associated file."""
        paper = await self.get_paper_by_id(paper_id)
        if not paper:
            return False
        
        # Delete the file from storage
        try:
            self.file_storage.delete_file(paper.file_path)
        except Exception as e:
            logger.warning(f"Could not delete file {paper.file_path}: {e}")
        
        # Delete from database (cascading will handle Document)
        await self.session.delete(paper)
        await self.session.commit()
        
        return True
    
    async def get_storage_stats(self) -> Dict:
        """Get storage statistics."""
        # Get file system stats
        fs_stats = self.file_storage.get_storage_stats()
        
        # Get database stats
        total_papers_stmt = select(func.count(ScientificPaper.id))
        total_papers_result = await self.session.execute(total_papers_stmt)
        total_papers = total_papers_result.scalar()
        
        # Papers by status
        status_stmt = select(
            ScientificPaper.processing_status,
            func.count(ScientificPaper.id)
        ).group_by(ScientificPaper.processing_status)
        status_result = await self.session.execute(status_stmt)
        status_counts = dict(status_result.fetchall())
        
        return {
            **fs_stats,
            'total_papers_db': total_papers,
            'papers_by_status': status_counts
        }
    
    def start_folder_watcher(self, user_id: str, search_space_id: int):
        """Start the folder watcher for automatic processing."""
        async def process_callback(file_path: str):
            """Callback for processing new files."""
            await self.process_pdf_file(
                file_path=file_path,
                user_id=user_id,
                search_space_id=search_space_id,
                move_file=True
            )
        
        folder_watcher_manager.initialize(config.WATCHED_FOLDER, process_callback)
        folder_watcher_manager.start()
        
        logger.info(f"Started folder watcher for user {user_id}, search_space {search_space_id}")
    
    def stop_folder_watcher(self):
        """Stop the folder watcher."""
        folder_watcher_manager.stop()
        logger.info("Stopped folder watcher")
    
    def get_watcher_status(self) -> Optional[Dict]:
        """Get folder watcher status."""
        return folder_watcher_manager.get_status()