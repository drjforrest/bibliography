import asyncio
import json
import logging
import redis.asyncio as redis
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class MigrationPhase(str, Enum):
    """Migration phases for tracking progress"""
    INITIALIZING = "initializing"
    MAPPING_DIRECTORIES = "mapping_directories"
    DISCOVERING_RECORDS = "discovering_records"
    MIGRATING_RECORDS = "migrating_records"
    GENERATING_LAY_SUMMARIES = "generating_lay_summaries"
    PROCESSING_CHUNKS = "processing_chunks"
    GENERATING_VECTORS = "generating_vectors"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class RecordStatus(str, Enum):
    """Individual record migration status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MigrationJobConfig:
    """Configuration for a migration job"""
    job_id: str
    user_id: str
    database_name: str
    search_space_id: int
    folder_path: Optional[str] = None
    force_resync: bool = False
    batch_size: int = 10
    max_retries: int = 3
    timeout_seconds: int = 3600  # 1 hour default


@dataclass
class MigrationProgress:
    """Current progress of a migration job"""
    job_id: str
    phase: MigrationPhase
    started_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    
    # Counts
    total_records: int = 0
    processed_records: int = 0
    completed_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    
    # Current processing info
    current_record: Optional[str] = None
    current_batch: Optional[List[str]] = None
    
    # Performance metrics
    records_per_minute: float = 0.0
    estimated_minutes_remaining: Optional[int] = None
    
    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0
    
    # Additional metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MigrationProgressTracker:
    """Redis-based progress tracker for DEVONthink migrations"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self._key_prefix = "migration:"
        self._job_ttl = 86400 * 7  # 1 week
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for migration tracking")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _job_key(self, job_id: str) -> str:
        """Get Redis key for job data"""
        return f"{self._key_prefix}job:{job_id}"
    
    def _progress_key(self, job_id: str) -> str:
        """Get Redis key for progress data"""
        return f"{self._key_prefix}progress:{job_id}"
    
    def _records_key(self, job_id: str) -> str:
        """Get Redis key for records set"""
        return f"{self._key_prefix}records:{job_id}"
    
    def _completed_key(self, job_id: str) -> str:
        """Get Redis key for completed records set"""
        return f"{self._key_prefix}completed:{job_id}"
    
    def _failed_key(self, job_id: str) -> str:
        """Get Redis key for failed records set"""
        return f"{self._key_prefix}failed:{job_id}"
    
    def _user_jobs_key(self, user_id: str) -> str:
        """Get Redis key for user's active jobs"""
        return f"{self._key_prefix}user_jobs:{user_id}"
    
    async def create_migration_job(self, config: MigrationJobConfig) -> str:
        """Create a new migration job"""
        await self.connect()
        
        job_key = self._job_key(config.job_id)
        progress_key = self._progress_key(config.job_id)
        user_jobs_key = self._user_jobs_key(config.user_id)
        
        # Store job config
        await self.redis_client.hset(job_key, mapping={
            "config": json.dumps(asdict(config)),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        })
        await self.redis_client.expire(job_key, self._job_ttl)
        
        # Initialize progress
        progress = MigrationProgress(
            job_id=config.job_id,
            phase=MigrationPhase.INITIALIZING,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        await self.redis_client.hset(progress_key, mapping={
            "data": json.dumps(asdict(progress), default=str)
        })
        await self.redis_client.expire(progress_key, self._job_ttl)
        
        # Track in user's active jobs
        await self.redis_client.sadd(user_jobs_key, config.job_id)
        await self.redis_client.expire(user_jobs_key, self._job_ttl)
        
        logger.info(f"Created migration job {config.job_id} for user {config.user_id}")
        return config.job_id
    
    async def update_phase(self, job_id: str, phase: MigrationPhase, metadata: Dict[str, Any] = None):
        """Update the current phase of migration"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if progress:
            progress.phase = phase
            progress.updated_at = datetime.now(timezone.utc)
            if metadata:
                progress.metadata.update(metadata)
            
            await self._save_progress(progress)
            logger.info(f"Job {job_id} moved to phase {phase.value}")
    
    async def set_total_records(self, job_id: str, total: int, record_uuids: List[str]):
        """Set the total number of records to process"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if progress:
            progress.total_records = total
            progress.updated_at = datetime.now(timezone.utc)
            await self._save_progress(progress)
        
        # Store all record UUIDs for tracking
        records_key = self._records_key(job_id)
        if record_uuids:
            await self.redis_client.sadd(records_key, *record_uuids)
            await self.redis_client.expire(records_key, self._job_ttl)
        
        logger.info(f"Job {job_id} set to process {total} records")
    
    async def mark_record_processing(self, job_id: str, record_uuid: str):
        """Mark a record as currently being processed"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if progress:
            progress.current_record = record_uuid
            progress.updated_at = datetime.now(timezone.utc)
            await self._save_progress(progress)
    
    async def mark_record_completed(self, job_id: str, record_uuid: str):
        """Mark a record as successfully completed"""
        await self.connect()
        
        completed_key = self._completed_key(job_id)
        await self.redis_client.sadd(completed_key, record_uuid)
        await self.redis_client.expire(completed_key, self._job_ttl)
        
        await self._update_counts(job_id)
        logger.debug(f"Job {job_id}: Record {record_uuid} completed")
    
    async def mark_record_failed(self, job_id: str, record_uuid: str, error: str):
        """Mark a record as failed"""
        await self.connect()
        
        failed_key = self._failed_key(job_id)
        await self.redis_client.hset(failed_key, record_uuid, json.dumps({
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))
        await self.redis_client.expire(failed_key, self._job_ttl)
        
        await self._update_counts(job_id)
        logger.warning(f"Job {job_id}: Record {record_uuid} failed - {error}")
    
    async def _update_counts(self, job_id: str):
        """Update progress counts from Redis sets"""
        await self.connect()
        
        completed_count = await self.redis_client.scard(self._completed_key(job_id))
        failed_count = await self.redis_client.hlen(self._failed_key(job_id))
        
        progress = await self.get_progress(job_id)
        if progress:
            progress.completed_records = completed_count
            progress.failed_records = failed_count
            progress.processed_records = completed_count + failed_count
            progress.updated_at = datetime.now(timezone.utc)
            
            # Calculate performance metrics
            elapsed_minutes = (progress.updated_at - progress.started_at).total_seconds() / 60
            if elapsed_minutes > 0:
                progress.records_per_minute = progress.processed_records / elapsed_minutes
                
                remaining_records = progress.total_records - progress.processed_records
                if progress.records_per_minute > 0:
                    progress.estimated_minutes_remaining = int(remaining_records / progress.records_per_minute)
            
            await self._save_progress(progress)
    
    async def get_progress(self, job_id: str) -> Optional[MigrationProgress]:
        """Get current progress for a job"""
        await self.connect()
        
        progress_key = self._progress_key(job_id)
        data = await self.redis_client.hget(progress_key, "data")
        
        if data:
            progress_dict = json.loads(data)
            # Convert datetime strings back to datetime objects
            progress_dict['started_at'] = datetime.fromisoformat(progress_dict['started_at'])
            progress_dict['updated_at'] = datetime.fromisoformat(progress_dict['updated_at'])
            if progress_dict.get('estimated_completion'):
                progress_dict['estimated_completion'] = datetime.fromisoformat(progress_dict['estimated_completion'])
            
            return MigrationProgress(**progress_dict)
        return None
    
    async def _save_progress(self, progress: MigrationProgress):
        """Save progress to Redis"""
        progress_key = self._progress_key(progress.job_id)
        await self.redis_client.hset(progress_key, "data", json.dumps(asdict(progress), default=str))
    
    async def get_failed_records(self, job_id: str) -> Dict[str, Dict]:
        """Get all failed records with error details"""
        await self.connect()
        
        failed_key = self._failed_key(job_id)
        failed_data = await self.redis_client.hgetall(failed_key)
        
        return {uuid: json.loads(data) for uuid, data in failed_data.items()}
    
    async def get_pending_records(self, job_id: str) -> Set[str]:
        """Get records that still need processing"""
        await self.connect()
        
        all_records = await self.redis_client.smembers(self._records_key(job_id))
        completed_records = await self.redis_client.smembers(self._completed_key(job_id))
        failed_records = set(await self.redis_client.hkeys(self._failed_key(job_id)))
        
        return set(all_records) - completed_records - failed_records
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused or failed job"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if not progress:
            return False
        
        if progress.phase in [MigrationPhase.PAUSED, MigrationPhase.FAILED]:
            progress.phase = MigrationPhase.MIGRATING_RECORDS  # Resume at migration phase
            progress.updated_at = datetime.now(timezone.utc)
            await self._save_progress(progress)
            logger.info(f"Resumed migration job {job_id}")
            return True
        
        return False
    
    async def pause_job(self, job_id: str):
        """Pause a running job"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if progress and progress.phase not in [MigrationPhase.COMPLETED, MigrationPhase.FAILED]:
            progress.phase = MigrationPhase.PAUSED
            progress.updated_at = datetime.now(timezone.utc)
            await self._save_progress(progress)
            logger.info(f"Paused migration job {job_id}")
    
    async def complete_job(self, job_id: str):
        """Mark job as completed"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if progress:
            progress.phase = MigrationPhase.COMPLETED
            progress.updated_at = datetime.now(timezone.utc)
            progress.estimated_completion = progress.updated_at
            await self._save_progress(progress)
            logger.info(f"Completed migration job {job_id}")
    
    async def fail_job(self, job_id: str, error: str):
        """Mark job as failed"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if progress:
            progress.phase = MigrationPhase.FAILED
            progress.last_error = error
            progress.error_count += 1
            progress.updated_at = datetime.now(timezone.utc)
            await self._save_progress(progress)
            logger.error(f"Failed migration job {job_id}: {error}")
    
    async def get_user_jobs(self, user_id: str) -> List[Dict]:
        """Get all jobs for a user"""
        await self.connect()
        
        user_jobs_key = self._user_jobs_key(user_id)
        job_ids = await self.redis_client.smembers(user_jobs_key)
        
        jobs = []
        for job_id in job_ids:
            progress = await self.get_progress(job_id)
            if progress:
                jobs.append({
                    "job_id": job_id,
                    "phase": progress.phase,
                    "started_at": progress.started_at,
                    "progress_percentage": (progress.processed_records / progress.total_records * 100) if progress.total_records > 0 else 0,
                    "records_completed": progress.completed_records,
                    "records_failed": progress.failed_records,
                    "records_total": progress.total_records
                })
        
        return jobs
    
    async def cleanup_completed_jobs(self, older_than_days: int = 7):
        """Clean up completed jobs older than specified days"""
        await self.connect()
        
        # This would typically scan for old jobs and clean them up
        # Implementation depends on your specific needs
        pass
    
    async def get_job_stats(self, job_id: str) -> Dict:
        """Get comprehensive job statistics"""
        await self.connect()
        
        progress = await self.get_progress(job_id)
        if not progress:
            return {}
        
        pending_count = len(await self.get_pending_records(job_id))
        failed_records = await self.get_failed_records(job_id)
        
        return {
            "job_id": job_id,
            "phase": progress.phase,
            "started_at": progress.started_at,
            "updated_at": progress.updated_at,
            "total_records": progress.total_records,
            "completed_records": progress.completed_records,
            "failed_records": progress.failed_records,
            "pending_records": pending_count,
            "progress_percentage": (progress.processed_records / progress.total_records * 100) if progress.total_records > 0 else 0,
            "records_per_minute": progress.records_per_minute,
            "estimated_minutes_remaining": progress.estimated_minutes_remaining,
            "error_count": progress.error_count,
            "last_error": progress.last_error,
            "failed_record_details": failed_records
        }


# Singleton instance
_tracker_instance: Optional[MigrationProgressTracker] = None


def get_migration_tracker(redis_url: str = "redis://localhost:6379/0") -> MigrationProgressTracker:
    """Get singleton migration tracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = MigrationProgressTracker(redis_url)
    return _tracker_instance