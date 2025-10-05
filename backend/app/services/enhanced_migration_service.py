import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.devonthink_sync_service import DevonthinkSyncService
from app.services.migration_progress_tracker import (
    MigrationProgressTracker, 
    MigrationJobConfig, 
    MigrationPhase,
    get_migration_tracker
)
from app.services.lay_summary_service import get_lay_summary_service
from app.db import SearchSpace, DevonthinkSync, DevonthinkSyncStatus

logger = logging.getLogger(__name__)


class EnhancedMigrationService:
    """Enhanced migration service with Redis progress tracking and resume capabilities"""
    
    def __init__(self, session: AsyncSession, redis_url: Optional[str] = None):
        self.session = session
        self.sync_service = DevonthinkSyncService(session)
        
        # Get Redis URL from environment or parameter
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.progress_tracker = get_migration_tracker(redis_url)
        
        # Initialize lay summary service
        self.lay_summary_service = get_lay_summary_service()
    
    async def start_complete_migration(self, database_name: str, user_id: UUID, 
                                     search_space_id: int, folder_path: Optional[str] = None,
                                     force_resync: bool = False) -> str:
        """Start a complete migration with progress tracking"""
        
        # Create unique job ID
        job_id = f"migration_{database_name}_{user_id}_{int(datetime.now().timestamp())}"
        
        # Create migration job config
        config = MigrationJobConfig(
            job_id=job_id,
            user_id=str(user_id),
            database_name=database_name,
            search_space_id=search_space_id,
            folder_path=folder_path,
            force_resync=force_resync,
            batch_size=10,  # Process 10 records at a time
            max_retries=3,
            timeout_seconds=7200  # 2 hours
        )
        
        # Create the job in Redis
        await self.progress_tracker.create_migration_job(config)
        
        # Start the migration in the background
        asyncio.create_task(self._execute_migration_pipeline(config))
        
        logger.info(f"Started complete migration job {job_id}")
        return job_id
    
    async def _execute_migration_pipeline(self, config: MigrationJobConfig):
        """Execute the complete migration pipeline with progress tracking"""
        job_id = config.job_id
        user_id = UUID(config.user_id)
        
        try:
            # Phase 1: Initialize
            logger.info(f"🚀 Phase 1: Initializing migration job {job_id}")
            await self.progress_tracker.update_phase(job_id, MigrationPhase.INITIALIZING)
            
            # Validate prerequisites
            logger.info(f"   🔍 Validating prerequisites...")
            if not await self._validate_prerequisites(config):
                logger.error(f"❌ Prerequisites validation failed for job {job_id}")
                await self.progress_tracker.fail_job(job_id, "Prerequisites validation failed")
                return
            logger.info(f"   ✅ Prerequisites validated successfully")
            
            # Phase 2: Map directories
            logger.info(f"🗺️ Phase 2: Mapping directory structure...")
            await self.progress_tracker.update_phase(job_id, MigrationPhase.MAPPING_DIRECTORIES)
            folder_count = await self._map_directories(config)
            await self.progress_tracker.update_phase(
                job_id, MigrationPhase.MAPPING_DIRECTORIES, 
                {"directories_mapped": folder_count}
            )
            logger.info(f"   ✅ Mapped {folder_count} directories")
            
            # Phase 3: Discover records
            logger.info(f"🔍 Phase 3: Discovering records to migrate...")
            await self.progress_tracker.update_phase(job_id, MigrationPhase.DISCOVERING_RECORDS)
            record_uuids = await self._discover_records(config)
            logger.info(f"   ✅ Discovered {len(record_uuids)} PDF records")
            
            # Filter out already completed records if not force_resync
            if not config.force_resync:
                logger.info(f"   🔍 Filtering out already synced records...")
                record_uuids = await self._filter_pending_records(record_uuids, user_id)
                logger.info(f"   ✅ {len(record_uuids)} records remaining after filtering")
            
            await self.progress_tracker.set_total_records(job_id, len(record_uuids), record_uuids)
            
            if not record_uuids:
                logger.info(f"ℹ️  No records to process - migration completed")
                await self.progress_tracker.complete_job(job_id)
                return
            
            # Phase 4: Migrate records
            logger.info(f"📦 Phase 4: Migrating {len(record_uuids)} records (PDF processing, chunking, vector embedding)...")
            await self.progress_tracker.update_phase(job_id, MigrationPhase.MIGRATING_RECORDS)
            await self._migrate_records_with_tracking(config, record_uuids)
            logger.info(f"✅ Record migration phase completed")
            
            # Phase 5: Generate lay summaries
            logger.info(f"🧠 Phase 5: Generating AI lay summaries...")
            await self.progress_tracker.update_phase(job_id, MigrationPhase.GENERATING_LAY_SUMMARIES)
            await self._generate_lay_summaries_for_migrated_records(config)
            logger.info(f"✅ Lay summary generation phase completed")
            
            # Phase 6: Complete
            logger.info(f"🎉 Phase 6: Finalizing migration job {job_id}")
            await self.progress_tracker.complete_job(job_id)
            logger.info(f"✅ Migration job {job_id} completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration job {job_id} failed with error: {str(e)}")
            logger.error(f"   📝 Error details: {type(e).__name__}")
            await self.progress_tracker.fail_job(job_id, str(e))
        finally:
            logger.debug(f"   🧹 Cleaning up resources for job {job_id}")
            await self.sync_service.close()
    
    async def _validate_prerequisites(self, config: MigrationJobConfig) -> bool:
        """Validate that all prerequisites are met"""
        try:
            # Check DEVONthink is running
            if not await self.sync_service.mcp_client.is_devonthink_running():
                logger.error("DEVONthink is not running")
                return False
            
            # Validate search space
            search_space = await self._get_search_space(config.search_space_id, UUID(config.user_id))
            if not search_space:
                logger.error(f"Search space {config.search_space_id} not found")
                return False
            
            # Validate database access
            databases = await self.sync_service.mcp_client.get_open_databases()
            if not any(db.get("name") == config.database_name for db in databases):
                logger.error(f"Database {config.database_name} not accessible")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Prerequisites validation failed: {str(e)}")
            return False
    
    async def _map_directories(self, config: MigrationJobConfig) -> int:
        """Map DEVONthink directory structure"""
        try:
            hierarchy = await self.sync_service._map_directory_hierarchy(
                config.database_name, 
                UUID(config.user_id), 
                config.folder_path
            )
            return len(hierarchy)
        except Exception as e:
            logger.error(f"Directory mapping failed: {str(e)}")
            raise
    
    async def _discover_records(self, config: MigrationJobConfig) -> List[str]:
        """Discover all records to be migrated"""
        try:
            # Search for PDF files
            search_query = "kind:pdf"
            pdf_records = await self.sync_service.mcp_client.search_records(
                search_query, database_name=config.database_name
            )
            
            # Filter by folder path if specified
            if config.folder_path:
                pdf_records = [
                    r for r in pdf_records 
                    if r.get("path", "").startswith(config.folder_path)
                ]
            
            return [record["uuid"] for record in pdf_records if "uuid" in record]
            
        except Exception as e:
            logger.error(f"Record discovery failed: {str(e)}")
            raise
    
    async def _filter_pending_records(self, record_uuids: List[str], user_id: UUID) -> List[str]:
        """Filter out records that are already successfully synced"""
        try:
            # Query for records that are already synced
            stmt = select(DevonthinkSync.dt_uuid).where(
                DevonthinkSync.user_id == user_id,
                DevonthinkSync.sync_status == DevonthinkSyncStatus.SYNCED,
                DevonthinkSync.dt_uuid.in_(record_uuids)
            )
            result = await self.session.execute(stmt)
            synced_uuids = {row[0] for row in result}
            
            # Return only unsynced records
            pending = [uuid for uuid in record_uuids if uuid not in synced_uuids]
            logger.info(f"Filtered {len(record_uuids)} records to {len(pending)} pending")
            return pending
            
        except Exception as e:
            logger.error(f"Record filtering failed: {str(e)}")
            # If filtering fails, process all records
            return record_uuids
    
    async def _migrate_records_with_tracking(self, config: MigrationJobConfig, record_uuids: List[str]):
        """Migrate records with detailed progress tracking"""
        job_id = config.job_id
        user_id = UUID(config.user_id)
        total_records = len(record_uuids)
        
        logger.info(f"🚀 Starting migration of {total_records} records for job {job_id}")
        
        # Process records in batches
        batch_size = config.batch_size
        processed_count = 0
        
        for i in range(0, len(record_uuids), batch_size):
            batch = record_uuids[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, total_records)
            
            logger.info(f"📦 Processing batch {batch_start}-{batch_end} of {total_records} records")
            
            # Check if job should continue (might be paused)
            progress = await self.progress_tracker.get_progress(job_id)
            if not progress or progress.phase == MigrationPhase.PAUSED:
                logger.info(f"⏸️  Migration job {job_id} paused, stopping processing")
                return
            
            # Process batch
            for j, record_uuid in enumerate(batch):
                current_record_num = processed_count + 1
                
                try:
                    # Mark as processing
                    await self.progress_tracker.mark_record_processing(job_id, record_uuid)
                    
                    # Get record details for logging
                    record_props = await self.sync_service.mcp_client.get_record_properties(
                        record_uuid=record_uuid
                    )
                    
                    if not record_props:
                        logger.error(f"❌ Record {current_record_num}/{total_records} ({record_uuid[:8]}...): Could not retrieve properties")
                        await self.progress_tracker.mark_record_failed(
                            job_id, record_uuid, "Could not retrieve record properties"
                        )
                        processed_count += 1
                        continue
                    
                    record_name = record_props.get('name', 'Unknown')
                    record_path = record_props.get('path', 'Unknown path')
                    
                    logger.info(f"📄 Processing record {current_record_num}/{total_records}: '{record_name}' ({record_uuid[:8]}...)")
                    logger.debug(f"   📁 Path: {record_path}")
                    
                    # Perform the actual sync with enhanced logging
                    sync_result = await self._sync_single_record_with_logging(
                        {"uuid": record_uuid, **record_props},
                        config.database_name,
                        user_id,
                        config.search_space_id,
                        config.force_resync,
                        current_record_num,
                        total_records
                    )
                    
                    if sync_result:
                        logger.info(f"✅ Completed record {current_record_num}/{total_records}: '{record_name}'")
                        # Mark as completed
                        await self.progress_tracker.mark_record_completed(job_id, record_uuid)
                    else:
                        logger.error(f"❌ Failed record {current_record_num}/{total_records}: '{record_name}' - Sync returned False")
                        await self.progress_tracker.mark_record_failed(job_id, record_uuid, "Sync operation returned False")
                    
                except Exception as e:
                    error_msg = f"Failed to sync record {record_uuid}: {str(e)}"
                    record_name = record_props.get('name', 'Unknown') if 'record_props' in locals() else 'Unknown'
                    logger.error(f"❌ Record {current_record_num}/{total_records} '{record_name}' failed: {str(e)}")
                    await self.progress_tracker.mark_record_failed(job_id, record_uuid, error_msg)
                
                processed_count += 1
            
            # Log batch completion
            logger.info(f"📦 Completed batch {batch_start}-{batch_end}. Progress: {processed_count}/{total_records} ({(processed_count/total_records*100):.1f}%)")
            
            # Small delay between batches to prevent overwhelming the system
            await asyncio.sleep(0.1)
    
    async def _sync_single_record_with_logging(self, record: Dict, database_name: str, 
                                             user_id: UUID, search_space_id: int, 
                                             force_resync: bool, current_num: int, total_num: int) -> bool:
        """Sync a single record with detailed step-by-step logging"""
        record_uuid = record.get('uuid')
        record_name = record.get('name', 'Unknown')
        
        try:
            logger.debug(f"   🔄 [{current_num}/{total_num}] Starting sync for '{record_name}'")
            
            # Step 1: Download and process PDF
            logger.debug(f"   💾 [{current_num}/{total_num}] Downloading PDF content...")
            
            # Call the original sync method but intercept its steps
            original_method = self.sync_service._sync_single_record
            
            # We need to replicate the sync logic with logging
            # First, check if record already exists and decide whether to skip
            from app.db import DevonthinkSync
            
            # Check existing sync status
            stmt = select(DevonthinkSync).where(
                DevonthinkSync.dt_uuid == record_uuid,
                DevonthinkSync.user_id == user_id
            )
            result = await self.session.execute(stmt)
            existing_sync = result.scalar_one_or_none()
            
            if existing_sync and not force_resync:
                if existing_sync.sync_status == DevonthinkSyncStatus.SYNCED:
                    logger.debug(f"   ⏭️  [{current_num}/{total_num}] Skipping '{record_name}' - already synced")
                    return True
            
            # Step 2: Get file content
            logger.debug(f"   📁 [{current_num}/{total_num}] Retrieving file content from DEVONthink...")
            
            try:
                file_content = await self.sync_service.mcp_client.get_record_content(record_uuid)
                if file_content:
                    logger.debug(f"   ✅ [{current_num}/{total_num}] Retrieved {len(file_content)} bytes of content")
                else:
                    logger.warning(f"   ⚠️  [{current_num}/{total_num}] No content retrieved for '{record_name}'")
            except Exception as e:
                logger.error(f"   ❌ [{current_num}/{total_num}] Failed to get content: {str(e)}")
                return False
            
            # Step 3: Process and store the record (delegate to original method)
            logger.debug(f"   🔄 [{current_num}/{total_num}] Processing and storing record...")
            
            # Call the original method
            sync_successful = await original_method(
                record, database_name, user_id, search_space_id, force_resync
            )
            
            if sync_successful:
                logger.debug(f"   💾 [{current_num}/{total_num}] Stored file and metadata to database")
                
                # Step 4: Text chunking (this happens inside the sync method)
                logger.debug(f"   ✂️  [{current_num}/{total_num}] Text chunking completed")
                
                # Step 5: Vector embedding and storage (this also happens inside)
                logger.debug(f"   🧠 [{current_num}/{total_num}] Vector embeddings generated and stored to pgvector")
                
                # Step 6: PostgreSQL metadata update
                logger.debug(f"   💾 [{current_num}/{total_num}] Metadata updated in PostgreSQL")
                
                return True
            else:
                logger.error(f"   ❌ [{current_num}/{total_num}] Sync operation failed for '{record_name}'")
                return False
            
        except Exception as e:
            logger.error(f"   ❌ [{current_num}/{total_num}] Exception during sync of '{record_name}': {str(e)}")
            return False
    
    async def resume_migration(self, job_id: str) -> bool:
        """Resume a paused or failed migration"""
        try:
            # Attempt to resume the job
            if not await self.progress_tracker.resume_job(job_id):
                return False
            
            # Get job config
            progress = await self.progress_tracker.get_progress(job_id)
            if not progress:
                return False
            
            # Get remaining records to process
            pending_records = await self.progress_tracker.get_pending_records(job_id)
            
            if not pending_records:
                # No more records to process
                await self.progress_tracker.complete_job(job_id)
                return True
            
            # Get job config from Redis
            job_data = await self.progress_tracker.redis_client.hget(
                self.progress_tracker._job_key(job_id), "config"
            )
            
            if not job_data:
                return False
            
            config_dict = json.loads(job_data)
            config = MigrationJobConfig(**config_dict)
            
            # Continue migration with remaining records
            await self._migrate_records_with_tracking(config, list(pending_records))
            
            # Mark as completed
            await self.progress_tracker.complete_job(job_id)
            logger.info(f"Successfully resumed and completed migration job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume migration {job_id}: {str(e)}")
            await self.progress_tracker.fail_job(job_id, f"Resume failed: {str(e)}")
            return False
    
    async def pause_migration(self, job_id: str) -> bool:
        """Pause a running migration"""
        try:
            await self.progress_tracker.pause_job(job_id)
            logger.info(f"Paused migration job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause migration {job_id}: {str(e)}")
            return False
    
    async def get_migration_status(self, job_id: str) -> Optional[Dict]:
        """Get detailed migration status"""
        try:
            return await self.progress_tracker.get_job_stats(job_id)
        except Exception as e:
            logger.error(f"Failed to get migration status for {job_id}: {str(e)}")
            return None
    
    async def list_user_migrations(self, user_id: UUID) -> List[Dict]:
        """List all migrations for a user"""
        try:
            return await self.progress_tracker.get_user_jobs(str(user_id))
        except Exception as e:
            logger.error(f"Failed to list migrations for user {user_id}: {str(e)}")
            return []
    
    async def retry_failed_records(self, job_id: str) -> bool:
        """Retry failed records in a migration"""
        try:
            # Get failed records
            failed_records = await self.progress_tracker.get_failed_records(job_id)
            if not failed_records:
                return True
            
            # Get job config
            job_data = await self.progress_tracker.redis_client.hget(
                self.progress_tracker._job_key(job_id), "config"
            )
            
            if not job_data:
                return False
            
            config_dict = json.loads(job_data)
            config = MigrationJobConfig(**config_dict)
            
            # Clear failed status and retry
            for record_uuid in failed_records.keys():
                await self.progress_tracker.redis_client.hdel(
                    self.progress_tracker._failed_key(job_id), record_uuid
                )
            
            # Retry the failed records
            await self._migrate_records_with_tracking(config, list(failed_records.keys()))
            
            logger.info(f"Retried {len(failed_records)} failed records for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry failed records for {job_id}: {str(e)}")
            return False
    
    async def _get_search_space(self, search_space_id: int, user_id: UUID) -> Optional[SearchSpace]:
        """Get and validate search space access"""
        stmt = select(SearchSpace).where(
            SearchSpace.id == search_space_id,
            SearchSpace.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _generate_lay_summaries_for_migrated_records(self, config: MigrationJobConfig):
        """Generate lay summaries for successfully migrated records"""
        job_id = config.job_id
        user_id = UUID(config.user_id)
        
        try:
            logger.info(f"🧠 Starting lay summary generation phase for job {job_id}")
            
            # First, test Ollama connection
            logger.debug(f"   🔌 Testing Ollama connection...")
            if not await self.lay_summary_service.test_connection():
                logger.warning(f"⚠️  Ollama not available for lay summary generation in job {job_id}")
                await self.progress_tracker.update_phase(
                    job_id, MigrationPhase.GENERATING_LAY_SUMMARIES,
                    {"skipped_reason": "Ollama not available"}
                )
                return
            
            logger.info(f"   ✅ Ollama connection successful")
            
            # Get completed records from Redis
            logger.debug(f"   🔍 Retrieving completed records from Redis...")
            completed_records = await self.progress_tracker.redis_client.smembers(
                self.progress_tracker._completed_key(job_id)
            )
            
            if not completed_records:
                logger.info(f"ℹ️  No completed records found for lay summary generation in job {job_id}")
                return
            
            total_records = len(completed_records)
            logger.info(f"📊 Generating lay summaries for {total_records} completed records")
            
            # Process records in smaller batches to avoid overwhelming Ollama
            batch_size = 5
            summaries_generated = 0
            summaries_failed = 0
            processed_summaries = 0
            
            for i in range(0, len(completed_records), batch_size):
                batch = list(completed_records)[i:i + batch_size]
                batch_start = i + 1
                batch_end = min(i + batch_size, total_records)
                
                logger.info(f"🧠 Processing lay summary batch {batch_start}-{batch_end} of {total_records}")
                
                # Check if job should continue
                progress = await self.progress_tracker.get_progress(job_id)
                if not progress or progress.phase == MigrationPhase.PAUSED:
                    logger.info(f"⏸️  Migration job {job_id} paused during lay summary generation")
                    return
                
                # Get paper data for this batch
                logger.debug(f"   📄 Retrieving paper data for batch...")
                papers_data = await self._get_papers_for_summary_generation(batch, user_id)
                
                if not papers_data:
                    logger.warning(f"   ⚠️  No papers found for batch {batch_start}-{batch_end}")
                    continue
                
                logger.debug(f"   ✅ Found {len(papers_data)} papers for lay summary generation")
                
                # Generate summaries for the batch
                logger.debug(f"   🧠 Generating lay summaries using Ollama (max 2 concurrent)...")
                batch_results = await self.lay_summary_service.generate_batch_summaries(
                    papers_data, max_concurrent=2  # Limit concurrency for Ollama
                )
                
                logger.info(f"   ✅ Generated {len(batch_results)} lay summaries in batch")
                
                # Update database with generated summaries
                for paper_id, summary in batch_results.items():
                    processed_summaries += 1
                    paper_data = next((p for p in papers_data if p['id'] == paper_id), None)
                    paper_title = paper_data['title'][:50] + '...' if paper_data and len(paper_data['title']) > 50 else (paper_data['title'] if paper_data else 'Unknown')
                    
                    try:
                        logger.debug(f"   💾 [{processed_summaries}/{total_records}] Updating lay summary for '{paper_title}'")
                        await self._update_paper_with_lay_summary(paper_id, summary)
                        summaries_generated += 1
                        logger.debug(f"   ✅ [{processed_summaries}/{total_records}] Lay summary updated ({len(summary)} chars)")
                    except Exception as e:
                        summaries_failed += 1
                        logger.error(f"   ❌ [{processed_summaries}/{total_records}] Failed to update lay summary for '{paper_title}': {str(e)}")
                
                # Log batch progress
                progress_pct = (processed_summaries / total_records * 100) if total_records > 0 else 0
                logger.info(f"📊 Lay summary progress: {processed_summaries}/{total_records} ({progress_pct:.1f}%) - {summaries_generated} successful, {summaries_failed} failed")
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            # Update progress with summary generation stats
            await self.progress_tracker.update_phase(
                job_id, MigrationPhase.GENERATING_LAY_SUMMARIES,
                {
                    "summaries_generated": summaries_generated,
                    "summaries_failed": summaries_failed,
                    "total_records": len(completed_records)
                }
            )
            
            success_rate = (summaries_generated / total_records * 100) if total_records > 0 else 0
            logger.info(f"🎉 Lay summary generation completed! Generated {summaries_generated}/{total_records} summaries ({success_rate:.1f}% success rate)")
            
            if summaries_failed > 0:
                logger.warning(f"⚠️  {summaries_failed} lay summary generations failed")
            
        except Exception as e:
            logger.error(f"❌ Error during lay summary generation for job {job_id}: {str(e)}")
            # Don't fail the entire migration for summary generation issues
    
    async def _get_papers_for_summary_generation(self, record_uuids: List[str], user_id: UUID) -> List[Dict]:
        """Get paper data needed for lay summary generation"""
        from app.db import ScientificPaper
        
        papers_data = []
        
        for dt_uuid in record_uuids:
            try:
                # Find the scientific paper by DEVONthink UUID
                stmt = select(ScientificPaper).where(
                    ScientificPaper.dt_source_uuid == dt_uuid
                )
                result = await self.session.execute(stmt)
                paper = result.scalar_one_or_none()
                
                if paper:
                    papers_data.append({
                        'id': paper.id,
                        'title': paper.title or 'Untitled',
                        'abstract': paper.abstract,
                        'full_text': paper.full_text[:5000] if paper.full_text else None  # Limit text size
                    })
                    
            except Exception as e:
                logger.error(f"Error getting paper data for {dt_uuid}: {str(e)}")
        
        return papers_data
    
    async def _update_paper_with_lay_summary(self, paper_id: int, lay_summary: str):
        """Update a scientific paper with its generated lay summary"""
        from app.db import ScientificPaper
        
        try:
            stmt = select(ScientificPaper).where(ScientificPaper.id == paper_id)
            result = await self.session.execute(stmt)
            paper = result.scalar_one_or_none()
            
            if paper:
                paper.lay_summary = lay_summary
                await self.session.commit()
                logger.debug(f"Updated lay summary for paper {paper_id}: {len(lay_summary)} characters")
            else:
                logger.error(f"Paper {paper_id} not found for lay summary update")
                
        except Exception as e:
            logger.error(f"Error updating lay summary for paper {paper_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        await self.sync_service.close()
        await self.progress_tracker.disconnect()
        await self.lay_summary_service.close()
