"""Redis-backed job queue for the video processing pipeline.

Pipeline work runs through RQ in a separate worker process (worker.py /
the `worker` docker-compose service) instead of FastAPI's in-process
BackgroundTasks. RQ's default Worker forks a new OS process per job, so a
crash or a forced kill of one job's process only ever takes down that one
job - the API server and any other in-flight jobs are unaffected. This
also gives us real cancellation (send_stop_job_command targets the exact
process running a job) and orphan detection (a VideoJob stuck in a
non-terminal status whose rq_job_id Redis no longer recognizes means its
worker died - see app.services.orphan_recovery).
"""

import logging

import redis
from rq import Queue
from rq.command import send_stop_job_command
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Job

from app.config import settings

logger = logging.getLogger(__name__)

# redis.from_url / Queue() don't actually open a connection until a command
# is issued, so constructing these at import time is safe even if Redis
# isn't reachable yet (e.g. during tests, which monkeypatch enqueue_pipeline
# instead of exercising this module for real).
_redis_conn = redis.from_url(settings.REDIS_URL)
pipeline_queue = Queue(
    "pipeline", connection=_redis_conn, default_timeout=settings.PIPELINE_JOB_TIMEOUT_SECONDS
)


def enqueue_pipeline(job_id: int) -> str:
    """Enqueue a pipeline run for `job_id`. Returns the RQ job id, which
    the caller should persist on the VideoJob row (rq_job_id) for later
    cancellation/orphan-detection."""
    # Local import: app.services.pipeline_service isn't needed anywhere
    # else in this module, and importing it lazily avoids import-order
    # issues since pipeline_service imports several other app.services.
    from app.services.pipeline_service import run_pipeline

    rq_job = pipeline_queue.enqueue(run_pipeline, job_id)
    logger.info("Enqueued pipeline job_id=%s as rq_job_id=%s", job_id, rq_job.id)
    return rq_job.id


def cancel_pipeline(rq_job_id: str) -> None:
    """Best-effort cancel: removes the job from the queue if it hasn't
    started yet, or asks the worker process executing it to stop if it
    has. Silently no-ops if the job is already gone/finished, or if Redis
    itself is unreachable - a broker blip shouldn't block the caller
    (e.g. the delete-job endpoint) from completing."""
    try:
        rq_job = Job.fetch(rq_job_id, connection=_redis_conn)
    except NoSuchJobError:
        return
    except redis.RedisError:
        logger.warning("Could not reach Redis to cancel rq_job_id=%s", rq_job_id)
        return

    try:
        if rq_job.is_started:
            send_stop_job_command(_redis_conn, rq_job_id)
            logger.info("Sent stop command for rq_job_id=%s", rq_job_id)
        elif rq_job.is_queued or rq_job.is_deferred or rq_job.is_scheduled:
            rq_job.cancel()
            logger.info("Cancelled queued rq_job_id=%s", rq_job_id)
    except InvalidJobOperation:
        # Job finished between the status check and the cancel/stop call -
        # nothing left to cancel.
        pass
    except redis.RedisError:
        logger.warning("Could not reach Redis to cancel rq_job_id=%s", rq_job_id)


def is_job_active(rq_job_id: str) -> bool:
    """True if Redis still knows about this job and it's genuinely
    in-progress. Used by orphan recovery to tell a genuinely in-progress
    job apart from one whose worker died. Treats an unreachable Redis as
    "active" (fail safe: don't mark jobs failed just because the broker
    is briefly unreachable).

    A job's own `status` field is set to "started" once a worker picks it
    up and is NEVER updated again by that worker until it finishes - if
    the worker is killed (crash, OOM, `docker kill`) mid-job, the job sits
    at status="started" in Redis forever, indistinguishable by status
    alone from one that's genuinely still running. So for a "started" job
    we additionally check that its recorded worker is still alive (RQ
    workers re-register a heartbeat key on an interval - see
    Worker.WORKER_TTL_SECONDS in worker.py). A worker that no longer
    appears in Worker.all() means its process is gone and the job it was
    holding is orphaned.
    """
    try:
        rq_job = Job.fetch(rq_job_id, connection=_redis_conn)
    except NoSuchJobError:
        return False
    except redis.RedisError:
        logger.warning("Could not reach Redis to check rq_job_id=%s; assuming active", rq_job_id)
        return True

    status = rq_job.get_status(refresh=True)
    if status in ("queued", "deferred", "scheduled"):
        return True
    if status == "started":
        worker_name = rq_job.worker_name
        if not worker_name:
            return False
        from rq.worker import Worker as RQWorker

        live_worker_names = {w.name for w in RQWorker.all(connection=_redis_conn)}
        return worker_name in live_worker_names
    return False
