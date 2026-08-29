"""RQ worker entrypoint for the video processing pipeline.

Runs as its own process/container (see the `worker` service in
docker-compose.yml), separate from the FastAPI API process. RQ's default
Worker forks a new OS process per job, so a crash or a forced kill of one
job only ever takes down that one job's forked process - this worker's
main process (and the API server, which is a different process/container
entirely) keeps running and picks up the next job.

Run directly with: python worker.py
"""

import logging

from redis import Redis
from rq import Worker

from app.config import settings
from app.database import SessionLocal
from app.services.orphan_recovery import recover_orphaned_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        recovered = recover_orphaned_jobs(db)
        if recovered:
            logger.warning("Recovered %d orphaned job(s) on worker startup", recovered)
    except Exception:  # noqa: BLE001 - must never block the worker from starting
        logger.exception("Orphaned-job recovery failed on worker startup (continuing anyway)")
    finally:
        db.close()

    conn = Redis.from_url(settings.REDIS_URL)
    # Short heartbeat TTL (RQ's default is 420s) so orphan recovery
    # (app.services.orphan_recovery, via app.queue.is_job_active) can tell
    # a crashed/killed worker apart from a live one within roughly a
    # minute instead of up to ~8 minutes.
    worker = Worker(["pipeline"], connection=conn, worker_ttl=30)
    logger.info("Worker starting, listening on queue 'pipeline'")
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
