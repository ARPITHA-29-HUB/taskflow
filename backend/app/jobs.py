"""
TaskFlow Background Jobs & Queue Demonstration (RQ Architecture)
----------------------------------------------------------------
This module demonstrates how background jobs transition from in-process
FastAPI BackgroundTasks to a durable, broker-backed message queue (RQ + Redis).

Architecture Comparison:
1. FastAPI BackgroundTasks:
   - In-process thread/task executed inside Uvicorn after HTTP response.
   - Zero additional infrastructure or network hops.
   - RISK: Process memory only! Server crash / restart / redeploy drops queued jobs permanently.

2. Durable Queue with Message Broker (RQ + Redis):
   - Producer (FastAPI): Enqueues job metadata into Redis list/stream and returns HTTP 201 immediately.
   - Broker (Redis): Persists job payload in memory / disk (survives API server restarts).
   - Consumer (RQ Worker): Independent Python process polling Redis queue, running jobs with retries.

Recommended for TaskFlow: RQ (Redis Queue)
- Why RQ over Celery?
  * TaskFlow already runs Redis for caching.
  * RQ is lightweight, Pythonic, and requires zero complex routing/exchange configuration.
  * Celery is feature-rich but significantly heavier with higher maintenance overhead.
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger("taskflow.jobs")


def send_task_reminder(task_id: str, title: str, due_date: str) -> str:
    """Worker job function to send a task reminder notification.
    
    This function is executed by the background worker process, completely
    isolated from the FastAPI web server.
    """
    logger.info(f"[RQ WORKER] Executing reminder for Task {task_id}: '{title}' (Due: {due_date})")
    # Future enhancement: Dispatch email via SMTP or push notification via webhook
    return f"Reminder sent for task {task_id}"


def enqueue_task_reminder(task_id: str, title: str, due_date: datetime):
    """Example helper demonstrating how to enqueue a durable reminder job into RQ.
    
    Usage in FastAPI endpoint:
        from app.jobs import enqueue_task_reminder
        enqueue_task_reminder(str(task.id), task.title, task.due_date)
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        from redis import Redis
        from rq import Queue

        redis_conn = Redis.from_url(redis_url)
        # Place job in dedicated 'reminders' queue
        queue = Queue("reminders", connection=redis_conn)
        
        job = queue.enqueue(
            send_task_reminder,
            task_id=str(task_id),
            title=title,
            due_date=due_date.isoformat(),
            job_timeout="3m",
        )
        logger.info(f"[RQ PRODUCER] Enqueued reminder job {job.id} for task {task_id}")
        return job.id
    except ImportError:
        logger.warning(
            "[RQ PRODUCER] 'rq' package is not installed. To run worker queue, install 'rq'."
        )
        return None
    except Exception as e:
        logger.error(f"[RQ PRODUCER] Failed to enqueue reminder to Redis broker: {e}")
        return None
