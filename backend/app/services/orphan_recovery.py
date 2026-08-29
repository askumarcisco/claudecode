"""Recovers VideoJob rows left stuck in a non-terminal status because the
worker process that was handling them died (crash, container restart,
manual kill) without ever reaching a terminal state.

Call recover_orphaned_jobs(db) once on startup (both the API and the
worker call it - see app.main and worker.py - so recovery happens
whichever process comes up first/last).
"""

import logging

from sqlalchemy.orm import Session

from app.models.video_job import JobStatus, VideoJob

logger = logging.getLogger(__name__)

_NON_TERMINAL_STATUSES = [
    JobStatus.queued,
    JobStatus.downloading,
    JobStatus.transcribing,
    JobStatus.analyzing,
    JobStatus.rendering,
]

_ORPHAN_MESSAGE = "Processing was interrupted (the worker handling this job stopped unexpectedly). Please resubmit."


def recover_orphaned_jobs(db: Session) -> int:
    """Mark non-terminal VideoJobs whose RQ job Redis no longer considers
    active as failed. Returns the number of jobs recovered."""
    from app.queue import is_job_active

    stuck_jobs = (
        db.query(VideoJob).filter(VideoJob.status.in_(_NON_TERMINAL_STATUSES)).all()
    )

    recovered = 0
    for job in stuck_jobs:
        if job.rq_job_id and is_job_active(job.rq_job_id):
            continue  # genuinely still in progress, leave it alone
        previous_status = job.status
        job.status = JobStatus.failed
        job.error_message = _ORPHAN_MESSAGE
        recovered += 1
        logger.warning("Recovered orphaned job_id=%s (was %s)", job.id, previous_status)

    if recovered:
        db.commit()

    return recovered
