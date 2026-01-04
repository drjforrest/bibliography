"""
Celery application configuration for HERO Evidence Library v2.0

This module initializes the Celery app for background task processing,
including podcast generation, summary creation, and other long-running operations.
"""

import os
from celery import Celery

# Import configuration
from app.config import config

# Create Celery instance
celery_app = Celery(
    "hero_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=[
        "app.tasks.podcast_tasks",
        "app.tasks.summary_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="America/Vancouver",  # Jamie's timezone
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Results
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # One task at a time for resource-intensive operations
    worker_max_tasks_per_child=50,  # Restart workers after 50 tasks to prevent memory leaks
    
    # Task routes (optional - for multiple queues)
    task_routes={
        "app.tasks.podcast_tasks.*": {"queue": "podcasts"},
        "app.tasks.summary_tasks.*": {"queue": "summaries"},
    },
    
    # Rate limiting (optional)
    task_annotations={
        "app.tasks.podcast_tasks.generate_content_podcast_task": {
            "rate_limit": "5/m"  # Max 5 podcasts per minute
        }
    }
)

# Optional: Configure Celery beat for periodic tasks
celery_app.conf.beat_schedule = {
    # Example: Clean up old podcast files every day
    "cleanup-old-podcasts": {
        "task": "app.tasks.podcast_tasks.cleanup_old_podcasts",
        "schedule": 86400.0,  # 24 hours
    },
}

if __name__ == "__main__":
    celery_app.start()
