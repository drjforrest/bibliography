import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import (
    DevonthinkSync, DevonthinkFolder, ScientificPaper, Document,
    DevonthinkSyncStatus, DocumentType, SearchSpace
)
from app.schemas.devonthink_schemas import (
    DevonthinkSyncRequest, DevonthinkSyncResponse, DevonthinkFolderHierarchy,
    DevonthinkRecordProperties
)
from app.services.devonthink_mcp_client import DevonthinkMCPClient
from app.services.pdf_processor import PDFProcessor
from app.services.file_storage import FileStorageService
from app.services.semantic_search_service import SemanticSearchService
from app.services.enhanced_rag_service import EnhancedRAGService
from app.services.embedding_service import EmbeddingService
from app.config import config

logger = logging.getLogger(__name__)


class DevonthinkSyncService:
    """Service for syncing DEVONthink database with bibliography system"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mcp_client = DevonthinkMCPClient()
        self.pdf_processor = PDFProcessor(session)
        self.file_storage = FileStorageService()
        self.semantic_search = SemanticSearchService(session)
        self.enhanced_rag = EnhancedRAGService(session)
        self.embedding_service = EmbeddingService(session)
    
    async def sync_database(self, request: DevonthinkSyncRequest, user_id: UUID) -> DevonthinkSyncResponse:
        """Main entry point for syncing DEVONthink database"""
        try:
            logger.info(f"Starting DEVONthink sync for user {user_id}, database: {request.database_name}")
            
            # Check if DEVONthink is running
            if not await self.mcp_client.is_devonthink_running():
                return DevonthinkSyncResponse(
                    success=False,
                    message="DEVONthink is not running. Please start DEVONthink and try again.",
                    details=["DEVONthink application not detected"]
                )
            
            # Get target search space
            search_space = await self._get_search_space(request.search_space_id, user_id)
            if not search_space:
                return DevonthinkSyncResponse(
                    success=False,
                    message="Search space not found or access denied",
                    details=[f"Search space ID {request.search_space_id} not accessible"]
                )
            
            response = DevonthinkSyncResponse(
                success=True,
                message="Sync initiated",
                details=[]
            )
            
            # Step 1: Map directory structure (optional - skip if get_open_databases fails)
            logger.info("Step 1: Mapping directory structure")
            try:
                hierarchy = await self._map_directory_hierarchy(request.database_name, user_id, request.folder_path)
                response.details.append(f"Mapped {len(hierarchy)} folders")
            except Exception as e:
                logger.warning(f"Directory mapping failed (continuing without it): {str(e)}")
                response.details.append("Directory mapping skipped due to MCP issue - sync will continue")
            
            # Step 2: Sync records
            logger.info("Step 2: Syncing records")
            sync_stats = await self._sync_records(
                request.database_name, user_id, search_space.id, 
                request.folder_path, request.force_resync
            )
            
            response.synced_count = sync_stats["synced"]
            response.error_count = sync_stats["errors"]
            response.skipped_count = sync_stats["skipped"]
            response.details.extend(sync_stats["details"])
            
            # Step 3: Rebuild FAISS vector store if we synced papers successfully
            if sync_stats["synced"] > 0:
                logger.info("Step 3: Rebuilding Enhanced RAG vector store")
                try:
                    rebuilt_success = await self.enhanced_rag.build_vector_store_from_papers(
                        user_id=str(user_id), search_space_id=search_space.id
                    )
                    if rebuilt_success:
                        stats = self.enhanced_rag.get_stats()
                        response.details.append(f"Rebuilt FAISS vector store with {stats.get('documents_indexed', 0)} documents")
                        logger.info("Successfully rebuilt Enhanced RAG vector store")
                    else:
                        response.details.append("Warning: Failed to rebuild FAISS vector store")
                except Exception as e:
                    logger.error(f"Error rebuilding FAISS vector store: {str(e)}")
                    response.details.append(f"Warning: FAISS rebuild failed: {str(e)}")
            
            if sync_stats["errors"] > 0:
                response.message = f"Sync completed with {sync_stats['errors']} errors"
            else:
                response.message = f"Sync completed successfully. {sync_stats['synced']} records synced and indexed."
            
            return response
            
        except Exception as e:
            logger.error(f"Error during DEVONthink sync: {str(e)}")
            return DevonthinkSyncResponse(
                success=False,
                message=f"Sync failed: {str(e)}",
                details=[f"Unexpected error: {str(e)}"]
            )
    
    async def _map_directory_hierarchy(self, database_name: str, user_id: UUID, 
                                     root_path: Optional[str] = None) -> List[DevonthinkFolderHierarchy]:
        """Map and store DEVONthink directory hierarchy"""
        try:
            # Start from root or specified path
            if root_path:
                root_records = await self.mcp_client.list_group_content(group_path=root_path, database_name=database_name)
            else:
                # Get database root
                databases = await self.mcp_client.get_open_databases()
                target_db = next((db for db in databases if db["name"] == database_name), None)
                if not target_db:
                    raise ValueError(f"Database '{database_name}' not found")
                
                root_records = await self.mcp_client.list_group_content(group_uuid=target_db["uuid"])
            
            hierarchy = []
            
            # Process each record recursively
            for record in root_records:
                if record.get("type") == "group":  # It's a folder
                    folder_hierarchy = await self._process_folder_recursive(
                        record, database_name, user_id, depth=0
                    )
                    hierarchy.append(folder_hierarchy)
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error mapping directory hierarchy: {str(e)}")
            raise
    
    async def _process_folder_recursive(self, folder_record: Dict, database_name: str, 
                                      user_id: UUID, depth: int = 0, 
                                      parent_uuid: Optional[str] = None) -> DevonthinkFolderHierarchy:
        """Recursively process a folder and its children"""
        folder_uuid = folder_record["uuid"]
        folder_name = folder_record["name"]
        folder_path = folder_record["path"]
        
        # Store/update folder in database
        await self._store_folder(folder_uuid, folder_path, folder_name, parent_uuid, depth, user_id)
        
        # Create hierarchy object
        hierarchy = DevonthinkFolderHierarchy(
            dt_uuid=folder_uuid,
            name=folder_name,
            dt_path=folder_path,
            parent_uuid=parent_uuid,
            depth=depth,
            children=[]
        )
        
        # Get folder contents
        folder_contents = await self.mcp_client.list_group_content(
            group_uuid=folder_uuid, database_name=database_name
        )
        
        # Process child folders
        for child_record in folder_contents:
            if child_record.get("type") == "group":
                child_hierarchy = await self._process_folder_recursive(
                    child_record, database_name, user_id, depth + 1, folder_uuid
                )
                hierarchy.children.append(child_hierarchy)
        
        return hierarchy
    
    async def _store_folder(self, dt_uuid: str, dt_path: str, folder_name: str,
                          parent_uuid: Optional[str], depth: int, user_id: UUID):
        """Store or update folder information in database"""
        try:
            # Check if folder already exists
            stmt = select(DevonthinkFolder).where(DevonthinkFolder.dt_uuid == dt_uuid)
            result = await self.session.execute(stmt)
            existing_folder = result.scalar_one_or_none()
            
            if existing_folder:
                # Update existing folder
                existing_folder.dt_path = dt_path
                existing_folder.folder_name = folder_name
                existing_folder.parent_dt_uuid = parent_uuid
                existing_folder.depth_level = depth
                existing_folder.sync_status = DevonthinkSyncStatus.SYNCED
                existing_folder.last_sync_date = datetime.now(timezone.utc)
            else:
                # Create new folder record
                new_folder = DevonthinkFolder(
                    dt_uuid=dt_uuid,
                    dt_path=dt_path,
                    folder_name=folder_name,
                    parent_dt_uuid=parent_uuid,
                    depth_level=depth,
                    sync_status=DevonthinkSyncStatus.SYNCED,
                    last_sync_date=datetime.now(timezone.utc),
                    user_id=user_id
                )
                self.session.add(new_folder)
            
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Error storing folder {dt_uuid}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def _sync_records(self, database_name: str, user_id: UUID, search_space_id: int,
                          folder_path: Optional[str] = None, force_resync: bool = False) -> Dict:
        """Sync PDF records from DEVONthink"""
        stats = {"synced": 0, "errors": 0, "skipped": 0, "details": []}
        
        try:
            # Search for PDF files in the specified database/folder
            search_query = "kind:pdf"
            if folder_path:
                pdf_records = await self.mcp_client.search_records(
                    search_query, database_name=database_name
                )
                # Filter by folder path
                pdf_records = [r for r in pdf_records if r.get("path", "").startswith(folder_path)]
            else:
                pdf_records = await self.mcp_client.search_records(
                    search_query, database_name=database_name
                )
            
            logger.info(f"Found {len(pdf_records)} PDF records to sync")
            
            for record in pdf_records:
                try:
                    await self._sync_single_record(record, database_name, user_id, search_space_id, force_resync)
                    stats["synced"] += 1
                    stats["details"].append(f"Synced: {record.get('name', 'Unknown')}")
                    
                except Exception as e:
                    stats["errors"] += 1
                    error_msg = f"Failed to sync {record.get('name', 'Unknown')}: {str(e)}"
                    stats["details"].append(error_msg)
                    logger.error(error_msg)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error syncing records: {str(e)}")
            raise
    
    async def _sync_single_record(self, record: Dict, database_name: str, user_id: UUID, 
                                search_space_id: int, force_resync: bool = False):
        """Sync a single PDF record from DEVONthink"""
        dt_uuid = record["uuid"]
        
        # Check if already synced
        if not force_resync:
            stmt = select(DevonthinkSync).where(DevonthinkSync.dt_uuid == dt_uuid)
            result = await self.session.execute(stmt)
            existing_sync = result.scalar_one_or_none()
            
            if existing_sync and existing_sync.sync_status == DevonthinkSyncStatus.SYNCED:
                logger.debug(f"Record {dt_uuid} already synced, skipping")
                return
        
        # Get detailed record properties
        record_props = await self.mcp_client.get_record_properties(record_uuid=dt_uuid)
        if not record_props:
            raise ValueError(f"Could not get properties for record {dt_uuid}")
        
        # Generate local UUID for the paper
        local_uuid = uuid4()
        
        # Create/update sync record
        sync_record = await self._create_or_update_sync_record(
            dt_uuid, local_uuid, record_props, user_id
        )
        
        try:
            # Step 1: Copy PDF binary with UUID naming
            pdf_path = await self._copy_pdf_binary(dt_uuid, local_uuid, record_props)
            
            # Step 2: Create scientific paper record
            paper = await self._create_scientific_paper(
                local_uuid, record_props, pdf_path, search_space_id, dt_uuid
            )
            
            # Step 3: Process for search (chunking and vectorization)
            await self._process_for_search(paper, search_space_id)
            
            # Update sync status
            sync_record.sync_status = DevonthinkSyncStatus.SYNCED
            sync_record.last_sync_date = datetime.now(timezone.utc)
            sync_record.scientific_paper_id = paper.id
            
            await self.session.commit()
            
        except Exception as e:
            sync_record.sync_status = DevonthinkSyncStatus.ERROR
            sync_record.error_message = str(e)
            await self.session.commit()
            raise
    
    async def _create_or_update_sync_record(self, dt_uuid: str, local_uuid: UUID,
                                          record_props: Dict, user_id: UUID) -> DevonthinkSync:
        """Create or update sync tracking record"""
        stmt = select(DevonthinkSync).where(DevonthinkSync.dt_uuid == dt_uuid)
        result = await self.session.execute(stmt)
        sync_record = result.scalar_one_or_none()
        
        if sync_record:
            sync_record.local_uuid = local_uuid
            sync_record.dt_path = record_props.get("path")
            sync_record.dt_modified_date = self._parse_datetime(record_props.get("modification_date"))
            sync_record.sync_status = DevonthinkSyncStatus.PENDING
            sync_record.error_message = None
        else:
            sync_record = DevonthinkSync(
                dt_uuid=dt_uuid,
                local_uuid=local_uuid,
                dt_path=record_props.get("path"),
                dt_modified_date=self._parse_datetime(record_props.get("modification_date")),
                sync_status=DevonthinkSyncStatus.PENDING,
                user_id=user_id
            )
            self.session.add(sync_record)
        
        await self.session.commit()
        return sync_record
    
    async def _copy_pdf_binary(self, dt_uuid: str, local_uuid: UUID, record_props: Dict) -> str:
        """Copy PDF binary from DEVONthink to local storage with UUID naming using direct file copy"""
        import tempfile
        import os
        import glob
        
        # Create temporary file path in home directory (accessible to DEVONthink)
        import os
        temp_dir = os.path.expanduser("~/tmp/devonthink_sync")
        os.makedirs(temp_dir, exist_ok=True)
        tmp_path = os.path.join(temp_dir, f"dt_copy_{local_uuid}.pdf")
        
        try:
            # Use new MCP method to copy file directly via AppleScript
            copy_result = await self.mcp_client.copy_record_to_path(dt_uuid, tmp_path)
            if not copy_result or not copy_result.get("success"):
                error_msg = copy_result.get("error", "Unknown error") if copy_result else "Copy failed"
                raise ValueError(f"Could not copy PDF for {dt_uuid}: {error_msg}")
            
            # DEVONthink creates a directory with the requested name, containing the actual PDF
            # Look for the actual PDF file inside the export directory
            actual_pdf_path = None
            if os.path.isdir(tmp_path):
                # Find PDF files in the export directory
                pdf_files = glob.glob(os.path.join(tmp_path, "*.pdf"))
                if pdf_files:
                    actual_pdf_path = pdf_files[0]  # Use the first PDF found
                    logger.info(f"Found exported PDF at: {actual_pdf_path}")
                else:
                    raise ValueError(f"No PDF files found in DEVONthink export directory: {tmp_path}")
            elif os.path.isfile(tmp_path):
                # If it's a file (shouldn't happen with DEVONthink export, but handle it)
                actual_pdf_path = tmp_path
            else:
                raise ValueError(f"DEVONthink export path doesn't exist: {tmp_path}")
            
            # Verify the file exists and has content
            if not os.path.exists(actual_pdf_path) or os.path.getsize(actual_pdf_path) == 0:
                raise ValueError(f"PDF file missing or empty: {actual_pdf_path}")
            
            # Use existing file storage service to organize and store the PDF
            relative_path, file_uuid = self.file_storage.store_pdf(actual_pdf_path)
            logger.info(f"Copied PDF {dt_uuid} to {relative_path} (size: {os.path.getsize(actual_pdf_path)} bytes)")
            return relative_path
            
        finally:
            # Clean up temporary files and directory
            if os.path.exists(tmp_path):
                if os.path.isdir(tmp_path):
                    # Remove directory and all its contents
                    import shutil
                    shutil.rmtree(tmp_path)
                else:
                    os.unlink(tmp_path)
    
    async def _create_scientific_paper(self, local_uuid: UUID, record_props: Dict,
                                     pdf_path: str, search_space_id: int, dt_uuid: str) -> ScientificPaper:
        """Create scientific paper record with extracted metadata"""
        # Convert relative path to absolute path for PDF processing
        from app.config import config
        import os
        
        if not os.path.isabs(pdf_path):
            absolute_pdf_path = os.path.join(config.PDF_STORAGE_ROOT, pdf_path)
        else:
            absolute_pdf_path = pdf_path
            
        # Extract text from PDF
        pdf_text = await self.pdf_processor.extract_text_from_file(absolute_pdf_path)
        
        # Extract metadata using existing PDF processor
        metadata = await self.pdf_processor.extract_metadata(absolute_pdf_path)
        
        # Create Document record first
        document = Document(
            title=record_props.get("name", "Unknown Document"),
            document_type=DocumentType.SCIENTIFIC_PAPER,
            content=pdf_text,
            search_space_id=search_space_id,
            document_metadata={
                "devonthink_source": dt_uuid,
                "devonthink_path": record_props.get("path"),
                "original_metadata": record_props
            }
        )
        self.session.add(document)
        await self.session.flush()  # Get document ID
        
        # Create scientific paper record with guaranteed non-null title
        extracted_title = metadata.get("title") or record_props.get("name") or "Untitled Document"
        # Clean filename extension if present
        if extracted_title.lower().endswith('.pdf'):
            extracted_title = extracted_title[:-4]
        
        paper = ScientificPaper(
            title=extracted_title,
            authors=metadata.get("authors", []),
            doi=metadata.get("doi"),
            abstract=metadata.get("abstract"),
            publication_date=self._parse_date(metadata.get("publication_date")),
            publication_year=metadata.get("publication_year"),
            file_path=pdf_path,
            file_size=record_props.get("size"),
            full_text=pdf_text,
            processing_status="completed",
            dt_source_uuid=dt_uuid,
            dt_source_path=record_props.get("path"),
            document_id=document.id,
            tags=record_props.get("tags", []),
            extraction_metadata={
                "devonthink_custom_fields": record_props.get("custom_meta_data", {}),
                "extraction_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        self.session.add(paper)
        await self.session.flush()
        
        return paper
    
    async def _process_for_search(self, paper: ScientificPaper, search_space_id: int):
        """Process paper for semantic search using both pgvector and Enhanced RAG"""
        try:
            # Step 1: Populate pgvector embeddings in PostgreSQL
            logger.info(f"Generating pgvector embeddings for paper {paper.id}")
            
            # Embed the document itself
            doc_embedded = await self.embedding_service.embed_document(paper.document_id)
            if doc_embedded:
                logger.info(f"Successfully embedded document {paper.document_id} in pgvector")
            
            # Create and embed chunks
            chunks_embedded = await self.embedding_service.create_and_embed_chunks(paper.document)
            if chunks_embedded:
                logger.info(f"Successfully created and embedded chunks for document {paper.document_id}")
            
            # Step 2: Also add to Enhanced RAG FAISS store for compatibility
            try:
                await self.enhanced_rag.add_paper_to_vector_store(paper)
                logger.info(f"Successfully added paper {paper.id} to Enhanced RAG FAISS vector store")
            except Exception as rag_error:
                logger.warning(f"Enhanced RAG indexing failed for paper {paper.id}: {str(rag_error)}")
                # Don't fail the whole process if just FAISS fails
            
        except Exception as e:
            logger.error(f"Error processing paper {paper.id} for search: {str(e)}")
            # Continue sync even if vectorization fails - documents are still stored
    
    async def monitor_changes(self, database_name: str = "Reference", days: int = 1) -> Dict:
        """Monitor DEVONthink for recent changes"""
        try:
            recent_records = await self.mcp_client.search_recent_changes(days, database_name)
            
            changes = {
                "new_records": [],
                "updated_records": [],
                "total_changes": len(recent_records)
            }
            
            for record in recent_records:
                if record.get("type") == "pdf":
                    # Check if we already have this record
                    stmt = select(DevonthinkSync).where(DevonthinkSync.dt_uuid == record["uuid"])
                    result = await self.session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if not existing:
                        changes["new_records"].append(record)
                    else:
                        # Check if modified since last sync
                        record_props = await self.mcp_client.get_record_properties(record_uuid=record["uuid"])
                        if record_props:
                            mod_date = self._parse_datetime(record_props.get("modification_date"))
                            if mod_date and existing.dt_modified_date and mod_date > existing.dt_modified_date:
                                changes["updated_records"].append(record)
            
            return changes
            
        except Exception as e:
            logger.error(f"Error monitoring changes: {str(e)}")
            raise
    
    async def _get_search_space(self, search_space_id: int, user_id: UUID) -> Optional[SearchSpace]:
        """Get and validate search space access"""
        stmt = select(SearchSpace).where(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from DEVONthink"""
        if not date_str:
            return None
        try:
            # Handle various datetime formats
            from dateutil import parser
            return parser.parse(date_str)
        except Exception:
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string"""
        dt = self._parse_datetime(date_str)
        return dt.date() if dt else None
    
    async def close(self):
        """Clean up resources"""
        await self.mcp_client.close()