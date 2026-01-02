import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db import (
    DevonthinkFolder,
    DevonthinkSync,
    DevonthinkSyncStatus,
    Document,
    DocumentType,
    ScientificPaper,
    SearchSpace,
)
from app.schemas.devonthink_schemas import (
    DevonthinkFolderHierarchy,
    DevonthinkSyncRequest,
    DevonthinkSyncResponse,
)
from app.services.devonthink_mcp_client import DevonthinkMCPClient

# TODO: EnhancedRAGService temporarily disabled due to deprecated langchain.chains.RetrievalQA
# Need to refactor to use modern langchain without RetrievalQA (deprecated in langchain 1.2.0)
# from app.services.enhanced_rag_service import EnhancedRAGService
from app.services.embedding_service import EmbeddingService
from app.services.file_storage import FileStorageService
from app.services.llm_enrichment_service import LLMEnrichmentService
from app.services.pdf_processor import PDFProcessor
from app.services.semantic_search_service import SemanticSearchService

logger = logging.getLogger(__name__)


class DevonthinkSyncService:
    """Service for syncing DEVONthink database with bibliography system"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mcp_client = DevonthinkMCPClient()
        self.pdf_processor = PDFProcessor(session)
        self.file_storage = FileStorageService()
        self.semantic_search = SemanticSearchService(session)
        # TODO: EnhancedRAGService temporarily disabled - see import comment above
        # self.enhanced_rag = EnhancedRAGService(session)
        self.embedding_service = EmbeddingService(session)
        self.llm_enrichment = LLMEnrichmentService(session)

    async def sync_database(
        self, request: DevonthinkSyncRequest, user_id: UUID
    ) -> DevonthinkSyncResponse:
        """Main entry point for syncing DEVONthink database"""
        try:
            logger.info(
                f"Starting DEVONthink sync for user {user_id}, database: {request.database_name}"
            )

            # Check if DEVONthink is running
            if not await self.mcp_client.is_devonthink_running():
                return DevonthinkSyncResponse(
                    success=False,
                    message="DEVONthink is not running. Please start DEVONthink and try again.",
                    details=["DEVONthink application not detected"],
                )

            # Get target search space
            search_space = await self._get_search_space(
                request.search_space_id, user_id
            )
            if not search_space:
                return DevonthinkSyncResponse(
                    success=False,
                    message="Search space not found or access denied",
                    details=[
                        f"Search space ID {request.search_space_id} not accessible"
                    ],
                )

            response = DevonthinkSyncResponse(
                success=True, message="Sync initiated", details=[]
            )

            # Step 1: Map directory structure (optional - skip if get_open_databases fails)
            logger.info("Step 1: Mapping directory structure")
            try:
                hierarchy = await self._map_directory_hierarchy(
                    request.database_name, user_id, request.folder_path
                )
                response.details.append(f"Mapped {len(hierarchy)} folders")
            except Exception as e:
                logger.warning(
                    f"Directory mapping failed (continuing without it): {str(e)}"
                )
                response.details.append(
                    "Directory mapping skipped due to MCP issue - sync will continue"
                )

            # Step 2: Sync records
            logger.info("Step 2: Syncing records")
            sync_stats = await self._sync_records(
                request.database_name,
                user_id,
                search_space.id,
                request.folder_path,
                request.force_resync,
            )

            response.synced_count = sync_stats["synced"]
            response.error_count = sync_stats["errors"]
            response.skipped_count = sync_stats["skipped"]
            response.details.extend(sync_stats["details"])

            # TODO: Step 3 temporarily disabled - EnhancedRAGService uses deprecated RetrievalQA
            # The pgvector embeddings in PostgreSQL are still being created in _process_for_search
            # Once EnhancedRAGService is refactored, uncomment this section
            # # Step 3: Rebuild FAISS vector store if we synced papers successfully
            # if sync_stats["synced"] > 0:
            #     logger.info("Step 3: Rebuilding Enhanced RAG vector store")
            #     try:
            #         rebuilt_success = (
            #             await self.enhanced_rag.build_vector_store_from_papers(
            #                 user_id=str(user_id), search_space_id=search_space.id
            #             )
            #         )
            #         if rebuilt_success:
            #             stats = self.enhanced_rag.get_stats()
            #             response.details.append(
            #                 f"Rebuilt FAISS vector store with {stats.get('documents_indexed', 0)} documents"
            #             )
            #             logger.info("Successfully rebuilt Enhanced RAG vector store")
            #         else:
            #             response.details.append(
            #                 "Warning: Failed to rebuild FAISS vector store"
            #             )
            #     except Exception as e:
            #         logger.error(f"Error rebuilding FAISS vector store: {str(e)}")
            #         response.details.append(f"Warning: FAISS rebuild failed: {str(e)}")

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
                details=[f"Unexpected error: {str(e)}"],
            )

    async def _map_directory_hierarchy(
        self, database_name: str, user_id: UUID, root_path: Optional[str] = None
    ) -> List[DevonthinkFolderHierarchy]:
        """Map and store DEVONthink directory hierarchy"""
        try:
            # Start from root or specified path
            if root_path:
                root_records = await self.mcp_client.list_group_content(
                    group_path=root_path, database_name=database_name
                )
            else:
                # Get database root
                databases = await self.mcp_client.get_open_databases()
                target_db = next(
                    (db for db in databases if db["name"] == database_name), None
                )
                if not target_db:
                    raise ValueError(f"Database '{database_name}' not found")

                root_records = await self.mcp_client.list_group_content(
                    group_uuid=target_db["uuid"]
                )

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

    async def _process_folder_recursive(
        self,
        folder_record: Dict,
        database_name: str,
        user_id: UUID,
        depth: int = 0,
        parent_uuid: Optional[str] = None,
    ) -> DevonthinkFolderHierarchy:
        """Recursively process a folder and its children"""
        folder_uuid = folder_record["uuid"]
        folder_name = folder_record["name"]
        folder_path = folder_record["path"]

        # Store/update folder in database
        await self._store_folder(
            folder_uuid, folder_path, folder_name, parent_uuid, depth, user_id
        )

        # Create hierarchy object
        hierarchy = DevonthinkFolderHierarchy(
            dt_uuid=folder_uuid,
            name=folder_name,
            dt_path=folder_path,
            parent_uuid=parent_uuid,
            depth=depth,
            children=[],
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

    async def _store_folder(
        self,
        dt_uuid: str,
        dt_path: str,
        folder_name: str,
        parent_uuid: Optional[str],
        depth: int,
        user_id: UUID,
    ):
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
                    user_id=user_id,
                )
                self.session.add(new_folder)

            await self.session.commit()

        except Exception as e:
            logger.error(f"Error storing folder {dt_uuid}: {str(e)}")
            await self.session.rollback()
            raise

    async def _sync_records(
        self,
        database_name: str,
        user_id: UUID,
        search_space_id: int,
        folder_path: Optional[str] = None,
        force_resync: bool = False,
    ) -> Dict:
        """Sync PDF records from DEVONthink"""
        stats = {"synced": 0, "errors": 0, "skipped": 0, "details": []}

        try:
            # Search for PDF files in the specified database
            search_query = "kind:pdf"
            logger.info(f"Searching for PDFs in database: {database_name}")
            pdf_records = await self.mcp_client.search_records(
                search_query, database_name=database_name
            )

            logger.info(f"Found {len(pdf_records)} records matching 'kind:pdf'")

            # Filter out annotations and non-PDF records
            def is_valid_pdf_record(record: Dict) -> bool:
                """Check if record is a valid PDF (not an annotation)"""
                # Get record type/kind
                record_type = record.get("recordType", "").lower()
                record_kind = record.get("kind", "").lower()
                name = record.get("name", "").lower()
                path = record.get("path", "").lower()

                # Exclude annotations explicitly
                if "annotation" in record_type or "annotation" in record_kind:
                    return False

                # Must have .pdf extension in name or path
                has_pdf_extension = (
                    name.endswith(".pdf")
                    or path.endswith(".pdf")
                    or record_type == "pdf document"
                )

                if not has_pdf_extension:
                    return False

                return True

            # Apply filters
            valid_pdf_records = [r for r in pdf_records if is_valid_pdf_record(r)]
            logger.info(
                f"Filtered to {len(valid_pdf_records)} valid PDF records (excluded {len(pdf_records) - len(valid_pdf_records)} annotations/non-PDFs)"
            )

            # Filter by folder path if specified
            if folder_path:
                valid_pdf_records = [
                    r
                    for r in valid_pdf_records
                    if r.get("path", "").startswith(folder_path)
                ]
                logger.info(
                    f"After folder filter ({folder_path}): {len(valid_pdf_records)} records"
                )

            pdf_records = valid_pdf_records

            for record in pdf_records:
                try:
                    await self._sync_single_record(
                        record, database_name, user_id, search_space_id, force_resync
                    )
                    stats["synced"] += 1
                    stats["details"].append(f"Synced: {record.get('name', 'Unknown')}")

                except Exception as e:
                    stats["errors"] += 1
                    error_msg = (
                        f"Failed to sync {record.get('name', 'Unknown')}: {str(e)}"
                    )
                    stats["details"].append(error_msg)
                    logger.error(error_msg)

            return stats

        except Exception as e:
            logger.error(f"Error syncing records: {str(e)}")
            raise

    async def _sync_single_record(
        self,
        record: Dict,
        database_name: str,
        user_id: UUID,
        search_space_id: int,
        force_resync: bool = False,
    ):
        """Sync a single PDF record from DEVONthink"""
        dt_uuid = record["uuid"]

        # Check if already synced
        if not force_resync:
            stmt = select(DevonthinkSync).where(DevonthinkSync.dt_uuid == dt_uuid)
            result = await self.session.execute(stmt)
            existing_sync = result.scalar_one_or_none()

            if (
                existing_sync
                and existing_sync.sync_status == DevonthinkSyncStatus.SYNCED
            ):
                logger.debug(f"Record {dt_uuid} already synced, skipping")
                return

        # Get detailed record properties
        record_props = await self.mcp_client.get_record_properties(record_uuid=dt_uuid)
        if not record_props:
            raise ValueError(f"Could not get properties for record {dt_uuid}")

        # Verify it's not an annotation and is from the correct database
        record_type = record_props.get("recordType", "").lower()
        record_kind = record_props.get("kind", "").lower()
        record_db = record_props.get("database", "")
        record_name = record_props.get("name", "").lower()

        # Skip annotations
        if "annotation" in record_type or "annotation" in record_kind:
            logger.warning(
                f"Skipping annotation record: {record_props.get('name', dt_uuid)}"
            )
            return

        # Verify database matches (if specified in properties)
        if record_db and database_name and record_db.lower() != database_name.lower():
            logger.warning(
                f"Record {dt_uuid} is in database '{record_db}', expected '{database_name}'. Skipping."
            )
            return

        # Verify it's actually a PDF
        if not record_name.endswith(".pdf") and record_type != "pdf document":
            logger.warning(
                f"Record {dt_uuid} ({record_props.get('name', 'Unknown')}) is not a PDF. Skipping."
            )
            return

        # Generate local UUID for the paper
        local_uuid = uuid4()

        # Create/update sync record
        sync_record = await self._create_or_update_sync_record(
            dt_uuid, local_uuid, record_props, user_id
        )

        try:
            # Step 1: Copy PDF binary with UUID naming
            pdf_path = await self._copy_pdf_binary(dt_uuid, local_uuid, record_props)

            # Step 2: Create scientific paper record (may return existing paper if DOI duplicate)
            # Store whether paper is new before calling (paper might not be flushed yet)
            paper_is_new = True
            paper = await self._create_scientific_paper(
                local_uuid, record_props, pdf_path, search_space_id, dt_uuid
            )

            # Check if paper is existing (loaded from DB) or new (just created)
            from sqlalchemy import inspect

            paper_insp = inspect(paper)
            paper_is_new = not paper_insp.persistent

            if not paper_is_new:
                # Existing paper - check what's missing and conditionally process
                logger.info(
                    f"📋 Paper {paper.id} already exists - checking what needs processing..."
                )
                needs_processing = await self._check_what_needs_processing(
                    paper, search_space_id
                )

                if needs_processing["embeddings"] or needs_processing["chunks"]:
                    logger.info(f"   🔍 Needs embeddings/chunks processing")
                    await self._process_embeddings_and_chunks(paper, search_space_id)
                else:
                    logger.debug(f"   ✓ Embeddings and chunks already exist")

                if needs_processing["enrichment"]:
                    logger.info(f"   🧠 Needs LLM enrichment")
                    await self._process_llm_enrichment(paper)
                else:
                    logger.debug(f"   ✓ LLM enrichment already complete")
            else:
                # New paper - process everything
                logger.debug(f"📄 Paper is new - processing everything")
                await self._process_for_search(paper, search_space_id)

            # Update sync status
            sync_record.sync_status = DevonthinkSyncStatus.SYNCED
            sync_record.last_sync_date = datetime.now(timezone.utc)
            sync_record.scientific_paper_id = paper.id

            await self.session.commit()
            return True

        except Exception as e:
            error_str = str(e)

            # Handle session rollback after errors
            try:
                await self.session.rollback()
            except:
                pass

            # Check if it's a duplicate DOI error
            if "duplicate key value violates unique constraint" in error_str and (
                "doi" in error_str.lower() or "ix_scientific_papers_doi" in error_str
            ):
                logger.warning(
                    f"Duplicate DOI detected for {dt_uuid}. Attempting to find existing paper and link sync record."
                )
                try:
                    # Try to extract DOI from metadata
                    import os

                    from app.config import config

                    # We already have pdf_path, try to get metadata
                    if not os.path.isabs(pdf_path):
                        absolute_pdf_path = os.path.join(
                            config.PDF_STORAGE_ROOT, pdf_path
                        )
                    else:
                        absolute_pdf_path = pdf_path

                    try:
                        metadata = await self.pdf_processor.extract_metadata(
                            absolute_pdf_path
                        )
                        doi = metadata.get("doi")
                        if doi:
                            stmt = select(ScientificPaper).where(
                                ScientificPaper.doi == doi
                            )
                            result = await self.session.execute(stmt)
                            existing_paper = result.scalar_one_or_none()
                            if existing_paper:
                                # Link sync record to existing paper
                                sync_record.scientific_paper_id = existing_paper.id
                                sync_record.sync_status = DevonthinkSyncStatus.SYNCED
                                sync_record.last_sync_date = datetime.now(timezone.utc)
                                await self.session.commit()
                                logger.info(
                                    f"✅ Linked DEVONthink record {dt_uuid} to existing paper (ID: {existing_paper.id}) with DOI {doi}"
                                )
                                return True
                    except Exception as meta_e:
                        logger.debug(
                            f"Could not extract metadata for duplicate check: {str(meta_e)}"
                        )

                    # If we can't find it by DOI, mark as error but don't fail completely
                    logger.warning(
                        f"Could not link duplicate DOI record {dt_uuid} to existing paper. Marking as error but continuing."
                    )
                except Exception as inner_e:
                    logger.error(
                        f"Error while trying to link to existing paper: {str(inner_e)}"
                    )

            sync_record.sync_status = DevonthinkSyncStatus.ERROR
            sync_record.error_message = error_str
            try:
                await self.session.commit()
            except:
                try:
                    await self.session.rollback()
                except:
                    pass
            logger.error(f"Error syncing record {dt_uuid}: {error_str}")
            return False

    async def _create_or_update_sync_record(
        self, dt_uuid: str, local_uuid: UUID, record_props: Dict, user_id: UUID
    ) -> DevonthinkSync:
        """Create or update sync tracking record"""
        stmt = select(DevonthinkSync).where(DevonthinkSync.dt_uuid == dt_uuid)
        result = await self.session.execute(stmt)
        sync_record = result.scalar_one_or_none()

        if sync_record:
            sync_record.local_uuid = local_uuid
            sync_record.dt_path = record_props.get("path")
            sync_record.dt_modified_date = self._parse_datetime(
                record_props.get("modification_date")
            )
            sync_record.sync_status = DevonthinkSyncStatus.PENDING
            sync_record.error_message = None
        else:
            sync_record = DevonthinkSync(
                dt_uuid=dt_uuid,
                local_uuid=local_uuid,
                dt_path=record_props.get("path"),
                dt_modified_date=self._parse_datetime(
                    record_props.get("modification_date")
                ),
                sync_status=DevonthinkSyncStatus.PENDING,
                user_id=user_id,
            )
            self.session.add(sync_record)

        await self.session.commit()
        return sync_record

    async def _copy_pdf_binary(
        self, dt_uuid: str, local_uuid: UUID, record_props: Dict
    ) -> str:
        """Copy PDF binary from DEVONthink to local storage with UUID naming"""
        import glob
        import os
        import shutil
        import tempfile

        # Create temporary file path in home directory
        temp_dir = os.path.expanduser("~/tmp/devonthink_sync")
        os.makedirs(temp_dir, exist_ok=True)
        tmp_path = os.path.join(temp_dir, f"dt_copy_{local_uuid}.pdf")

        try:
            # Try Method 1: Read directly from DEVONthink file path if available
            devonthink_path = record_props.get("path")
            if devonthink_path and os.path.exists(devonthink_path):
                logger.info(
                    f"Reading PDF directly from DEVONthink path: {devonthink_path}"
                )
                shutil.copy2(devonthink_path, tmp_path)
            else:
                # Method 2: Try to construct path from UUID
                # DEVONthink stores PDFs in: Database.dtBase2/Files.noindex/pdf/{uuid}.pdf
                # We need to find the database path first
                if devonthink_path:
                    # Extract database base path (everything before /Files.noindex)
                    if "/Files.noindex" in devonthink_path:
                        db_base = devonthink_path.split("/Files.noindex")[0]
                        # Try the UUID-based path
                        uuid_path = os.path.join(
                            db_base, "Files.noindex", "pdf", f"{dt_uuid}.pdf"
                        )
                        if os.path.exists(uuid_path):
                            logger.info(f"Found PDF at constructed path: {uuid_path}")
                            shutil.copy2(uuid_path, tmp_path)
                        else:
                            raise ValueError(
                                f"PDF file not found at DEVONthink path: {devonthink_path} or {uuid_path}"
                            )
                    else:
                        # Try the path as-is
                        if os.path.exists(devonthink_path):
                            shutil.copy2(devonthink_path, tmp_path)
                        else:
                            raise ValueError(
                                f"PDF file not found at DEVONthink path: {devonthink_path}"
                            )
                else:
                    # Method 3: Use AppleScript to get PDF binary directly (like the user's export script)
                    logger.info(
                        f"No path in record_props for {dt_uuid}, trying AppleScript export"
                    )
                    try:
                        from app.services.devonthink_applescript_helper import (
                            get_pdf_binary_from_devonthink,
                        )

                        database_name = record_props.get("database") or "BIBLIOGRAPHY"
                        pdf_data = get_pdf_binary_from_devonthink(
                            dt_uuid, database_name
                        )

                        # Write to temp file
                        with open(tmp_path, "wb") as f:
                            f.write(pdf_data)

                        logger.info(
                            f"Successfully exported PDF via AppleScript for {dt_uuid}"
                        )
                    except Exception as e:
                        logger.error(f"AppleScript export failed: {str(e)}")
                        raise ValueError(
                            f"Cannot retrieve PDF for {dt_uuid}: File path not available and AppleScript export failed: {str(e)}"
                        )

            # Verify file was written and is a valid PDF
            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                raise ValueError(f"Failed to copy PDF file for {dt_uuid}")

            # Check PDF header
            with open(tmp_path, "rb") as f:
                header = f.read(4)
                if header != b"%PDF":
                    logger.warning(
                        f"File doesn't start with PDF header: {header}, but continuing anyway"
                    )

            # Store the PDF using the file storage service
            from app.services.file_storage import FileStorageService

            file_storage = FileStorageService()
            relative_path, file_uuid = file_storage.store_pdf(tmp_path)
            logger.info(
                f"Stored PDF {dt_uuid} to {relative_path} (size: {os.path.getsize(tmp_path)} bytes)"
            )

            # Clean up temp file
            try:
                os.remove(tmp_path)
            except:
                pass

            return relative_path

        except Exception as e:
            # Clean up on error
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
            raise ValueError(f"Could not copy PDF for {dt_uuid}: {str(e)}")

    async def _create_scientific_paper(
        self,
        local_uuid: UUID,
        record_props: Dict,
        pdf_path: str,
        search_space_id: int,
        dt_uuid: str,
    ) -> ScientificPaper:
        """Create scientific paper record with extracted metadata"""
        # Convert relative path to absolute path for PDF processing
        import os

        from app.config import config

        if not os.path.isabs(pdf_path):
            absolute_pdf_path = os.path.join(config.PDF_STORAGE_ROOT, pdf_path)
        else:
            absolute_pdf_path = pdf_path

        # Extract text from PDF
        pdf_text = await self.pdf_processor.extract_text_from_file(absolute_pdf_path)

        # Extract metadata using existing PDF processor
        metadata = await self.pdf_processor.extract_metadata(absolute_pdf_path)

        # Check for duplicate by DOI before creating
        doi = metadata.get("doi")
        if doi:
            stmt = select(ScientificPaper).where(ScientificPaper.doi == doi)
            result = await self.session.execute(stmt)
            existing_paper = result.scalar_one_or_none()
            if existing_paper:
                logger.info(
                    f"📋 Paper with DOI {doi} already exists (ID: {existing_paper.id}, title: {existing_paper.title}). "
                    f"Linking sync record to existing paper and updating metadata if needed."
                )
                # Update metadata if it's missing or incomplete
                await self._update_paper_metadata_if_needed(
                    existing_paper, metadata, record_props, pdf_path, dt_uuid
                )
                # Return existing paper - caller will link sync record to it
                return existing_paper

        # Create Document record first
        document = Document(
            title=record_props.get("name", "Unknown Document"),
            document_type=DocumentType.SCIENTIFIC_PAPER,
            content=pdf_text,
            search_space_id=search_space_id,
            document_metadata={
                "devonthink_source": dt_uuid,
                "devonthink_path": record_props.get("path"),
                "original_metadata": record_props,
            },
        )
        self.session.add(document)
        await self.session.flush()  # Get document ID

        # Create scientific paper record with guaranteed non-null title
        extracted_title = (
            metadata.get("title") or record_props.get("name") or "Untitled Document"
        )
        # Clean filename extension if present
        if extracted_title.lower().endswith(".pdf"):
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
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        self.session.add(paper)
        await self.session.flush()

        return paper

    async def _check_what_needs_processing(
        self, paper: ScientificPaper, search_space_id: int
    ) -> Dict[str, bool]:
        """Check what processing is needed for an existing paper"""
        needs = {
            "embeddings": False,
            "chunks": False,
            "enrichment": False,
        }

        try:
            # Check if document has embedding (eagerly load chunks to avoid lazy loading issues)
            from sqlalchemy.orm import selectinload

            stmt = (
                select(Document)
                .where(Document.id == paper.document_id)
                .options(selectinload(Document.chunks))
            )
            result = await self.session.execute(stmt)
            document = result.scalar_one_or_none()

            if document:
                # Check embeddings - handle numpy arrays/vectors properly
                if document.embedding is None:
                    needs["embeddings"] = True
                else:
                    # Check if embedding is effectively empty
                    try:
                        # Try to get length if it's an array-like object
                        if hasattr(document.embedding, "__len__"):
                            if len(document.embedding) == 0:
                                needs["embeddings"] = True
                        # If it's a string representation, check that
                        elif isinstance(document.embedding, str):
                            if len(document.embedding.strip()) == 0:
                                needs["embeddings"] = True
                    except (TypeError, AttributeError):
                        # If we can't determine, assume it needs processing
                        needs["embeddings"] = True

                # Check chunks
                chunks_list = list(document.chunks) if document.chunks else []
                if not chunks_list or len(chunks_list) == 0:
                    needs["chunks"] = True
                else:
                    # Check if chunks have embeddings
                    for chunk in chunks_list:
                        if chunk.embedding is None:
                            needs["chunks"] = True
                            break
                        # Check if embedding is effectively empty
                        try:
                            if hasattr(chunk.embedding, "__len__"):
                                if len(chunk.embedding) == 0:
                                    needs["chunks"] = True
                                    break
                            elif isinstance(chunk.embedding, str):
                                if len(chunk.embedding.strip()) == 0:
                                    needs["chunks"] = True
                                    break
                        except (TypeError, AttributeError):
                            # If we can't determine, assume it needs processing
                            needs["chunks"] = True
                            break

            # Check LLM enrichment
            metadata = paper.extraction_metadata or {}
            has_lay_summary = paper.lay_summary and len(paper.lay_summary.strip()) > 0
            has_short_desc = bool(metadata.get("short_description"))
            has_insights = bool(metadata.get("insights"))
            has_citations = bool(metadata.get("citations"))

            if not (
                has_lay_summary and has_short_desc and has_insights and has_citations
            ):
                needs["enrichment"] = True
                logger.debug(
                    f"   Enrichment status: lay_summary={has_lay_summary}, "
                    f"short_desc={has_short_desc}, insights={has_insights}, citations={has_citations}"
                )

        except Exception as e:
            logger.warning(f"Error checking processing needs: {str(e)}")
            # If check fails, assume everything needs processing to be safe
            needs = {"embeddings": True, "chunks": True, "enrichment": True}

        return needs

    async def _process_embeddings_and_chunks(
        self, paper: ScientificPaper, search_space_id: int
    ):
        """Process embeddings and chunks for a paper"""
        try:
            logger.info(f"Generating pgvector embeddings for paper {paper.id}")

            # Query document explicitly with eager loading to avoid lazy loading issues
            from sqlalchemy.orm import selectinload

            stmt = (
                select(Document)
                .where(Document.id == paper.document_id)
                .options(selectinload(Document.chunks))
            )
            result = await self.session.execute(stmt)
            document = result.scalar_one()

            # Embed the document itself
            doc_embedded = await self.embedding_service.embed_document(
                paper.document_id
            )
            if doc_embedded:
                logger.info(
                    f"Successfully embedded document {paper.document_id} in pgvector"
                )

            # Ensure document content is loaded
            if not document.content:
                logger.warning(
                    f"Document {document.id} has no content, skipping chunk creation"
                )
                return

            # Create and embed chunks
            chunks_embedded = await self.embedding_service.create_and_embed_chunks(
                document
            )
            if chunks_embedded:
                logger.info(
                    f"Successfully created and embedded chunks for document {paper.document_id}"
                )

        except Exception as e:
            logger.error(
                f"Error processing embeddings/chunks for paper {paper.id}: {str(e)}"
            )
            raise

    async def _process_llm_enrichment(self, paper: ScientificPaper):
        """Process LLM enrichment for a paper"""
        try:
            logger.info(f"Running LLM enrichment for paper {paper.id}")
            enriched = await self.llm_enrichment.enrich_paper(paper.id)
            if enriched:
                await self.session.commit()  # Commit enrichment changes
                logger.info(
                    f"Successfully enriched paper {paper.id} with LLM-generated content"
                )
            else:
                logger.warning(f"LLM enrichment returned False for paper {paper.id}")
        except Exception as e:
            logger.error(f"LLM enrichment failed for paper {paper.id}: {str(e)}")
            # Don't raise - enrichment failure shouldn't block sync

    async def _update_paper_metadata_if_needed(
        self,
        paper: ScientificPaper,
        metadata: Dict,
        record_props: Dict,
        pdf_path: str,
        dt_uuid: str,
    ):
        """Update paper metadata if it's missing or incomplete"""
        updated = False

        # Update title if missing
        if not paper.title or paper.title == "Untitled Document":
            new_title = metadata.get("title") or record_props.get(
                "name", "Untitled Document"
            )
            if new_title.lower().endswith(".pdf"):
                new_title = new_title[:-4]
            if new_title != paper.title:
                paper.title = new_title
                updated = True
                logger.debug(f"   Updated title for paper {paper.id}")

        # Update authors if missing
        if not paper.authors and metadata.get("authors"):
            paper.authors = metadata.get("authors")
            updated = True
            logger.debug(f"   Updated authors for paper {paper.id}")

        # Update abstract if missing
        if not paper.abstract and metadata.get("abstract"):
            paper.abstract = metadata.get("abstract")
            updated = True
            logger.debug(f"   Updated abstract for paper {paper.id}")

        # Update publication info if missing
        if not paper.publication_year and metadata.get("publication_year"):
            paper.publication_year = metadata.get("publication_year")
            updated = True
        if not paper.publication_date and metadata.get("publication_date"):
            paper.publication_date = self._parse_date(metadata.get("publication_date"))
            updated = True

        # Update file info if missing
        if not paper.file_path:
            paper.file_path = pdf_path
            updated = True
        if not paper.file_size and record_props.get("size"):
            paper.file_size = record_props.get("size")
            updated = True

        # Update DEVONthink source info
        if not paper.dt_source_uuid:
            paper.dt_source_uuid = dt_uuid
            updated = True
        if not paper.dt_source_path:
            paper.dt_source_path = record_props.get("path")
            updated = True

        # Update full_text if missing (from document content)
        if not paper.full_text:
            try:
                import os

                from app.config import config

                if not os.path.isabs(pdf_path):
                    absolute_pdf_path = os.path.join(config.PDF_STORAGE_ROOT, pdf_path)
                else:
                    absolute_pdf_path = pdf_path
                pdf_text = await self.pdf_processor.extract_text_from_file(
                    absolute_pdf_path
                )
                if pdf_text:
                    paper.full_text = pdf_text
                    updated = True
                    logger.debug(f"   Updated full_text for paper {paper.id}")
            except Exception as e:
                logger.debug(f"   Could not update full_text: {str(e)}")

        if updated:
            await self.session.flush()
            logger.info(f"   ✅ Updated metadata for existing paper {paper.id}")

    async def _process_for_search(self, paper: ScientificPaper, search_space_id: int):
        """Process paper for semantic search using pgvector and LLM enrichment"""
        try:
            # Step 1: Populate pgvector embeddings in PostgreSQL
            logger.info(f"Generating pgvector embeddings for paper {paper.id}")

            # Embed the document itself
            doc_embedded = await self.embedding_service.embed_document(
                paper.document_id
            )
            if doc_embedded:
                logger.info(
                    f"Successfully embedded document {paper.document_id} in pgvector"
                )

            # Query document explicitly to avoid lazy loading issues after async operations
            # The paper.document relationship can't be accessed after greenlet context changes
            stmt = select(Document).where(Document.id == paper.document_id)
            result = await self.session.execute(stmt)
            document = result.scalar_one()

            # Ensure document content is loaded
            if not document.content:
                logger.warning(
                    f"Document {document.id} has no content, skipping chunk creation"
                )
                chunks_embedded = False
            else:
                # Create and embed chunks
                chunks_embedded = await self.embedding_service.create_and_embed_chunks(
                    document
                )
            if chunks_embedded:
                logger.info(
                    f"Successfully created and embedded chunks for document {paper.document_id}"
                )

            # Step 2: LLM enrichment (lay summary, short description, insights, citations)
            logger.info(f"Running LLM enrichment for paper {paper.id}")
            try:
                enriched = await self.llm_enrichment.enrich_paper(paper.id)
                if enriched:
                    logger.info(
                        f"Successfully enriched paper {paper.id} with LLM-generated content"
                    )
                else:
                    logger.warning(
                        f"LLM enrichment returned False for paper {paper.id}"
                    )
            except Exception as e:
                logger.error(f"LLM enrichment failed for paper {paper.id}: {str(e)}")
                # Continue sync even if LLM enrichment fails

            # TODO: Step 3 temporarily disabled - EnhancedRAGService uses deprecated RetrievalQA
            # pgvector embeddings are still being created above, which is the primary search backend
            # Once EnhancedRAGService is refactored, uncomment this section
            # # Step 3: Also add to Enhanced RAG FAISS store for compatibility
            # try:
            #     await self.enhanced_rag.add_paper_to_vector_store(paper)
            #     logger.info(
            #         f"Successfully added paper {paper.id} to Enhanced RAG FAISS vector store"
            #     )
            # except Exception as rag_error:
            #     logger.warning(
            #         f"Enhanced RAG indexing failed for paper {paper.id}: {str(rag_error)}"
            #     )
            #     # Don't fail the whole process if just FAISS fails

        except Exception as e:
            logger.error(f"Error processing paper {paper.id} for search: {str(e)}")
            # Continue sync even if vectorization/enrichment fails - documents are still stored

    async def monitor_changes(
        self, database_name: str = "Reference", days: int = 1
    ) -> Dict:
        """Monitor DEVONthink for recent changes"""
        try:
            recent_records = await self.mcp_client.search_recent_changes(
                days, database_name
            )

            changes = {
                "new_records": [],
                "updated_records": [],
                "total_changes": len(recent_records),
            }

            for record in recent_records:
                if record.get("type") == "pdf":
                    # Check if we already have this record
                    stmt = select(DevonthinkSync).where(
                        DevonthinkSync.dt_uuid == record["uuid"]
                    )
                    result = await self.session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if not existing:
                        changes["new_records"].append(record)
                    else:
                        # Check if modified since last sync
                        record_props = await self.mcp_client.get_record_properties(
                            record_uuid=record["uuid"]
                        )
                        if record_props:
                            mod_date = self._parse_datetime(
                                record_props.get("modification_date")
                            )
                            if (
                                mod_date
                                and existing.dt_modified_date
                                and mod_date > existing.dt_modified_date
                            ):
                                changes["updated_records"].append(record)

            return changes

        except Exception as e:
            logger.error(f"Error monitoring changes: {str(e)}")
            raise

    async def _get_search_space(
        self, search_space_id: int, user_id: UUID
    ) -> Optional[SearchSpace]:
        """Get and validate search space access"""
        stmt = select(SearchSpace).where(
            SearchSpace.id == search_space_id, SearchSpace.user_id == user_id
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
