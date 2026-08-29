import logging
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.video_job import JobStatus, SourceType, VideoJob

logger = logging.getLogger(__name__)

# Defense-in-depth allowlist: restrict submitted URLs to actual YouTube hosts
# rather than handing arbitrary user-controlled strings to yt-dlp, which
# supports hundreds of extractor sites (including a generic URL extractor)
# and could otherwise be used to probe internal/unexpected hosts.
_ALLOWED_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def _validate_youtube_url(youtube_url: str) -> str:
    candidate = (youtube_url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValidationError("youtube_url must be a valid http(s) URL")
    if parsed.hostname is None or parsed.hostname.lower() not in _ALLOWED_YOUTUBE_HOSTS:
        raise ValidationError("youtube_url must be a youtube.com or youtu.be URL")
    return candidate


def create_job_from_url(db: Session, user_id: int, youtube_url: str) -> VideoJob:
    youtube_url = _validate_youtube_url(youtube_url)
    job = VideoJob(
        user_id=user_id,
        source_type=SourceType.youtube_url,
        youtube_url=youtube_url,
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Created job id=%s from URL for user_id=%s", job.id, user_id)
    return job


def create_job_from_upload(db: Session, user_id: int, uploaded_file_path: str) -> VideoJob:
    job = VideoJob(
        user_id=user_id,
        source_type=SourceType.upload,
        uploaded_file_path=uploaded_file_path,
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Created job id=%s from upload for user_id=%s", job.id, user_id)
    return job


def get_job(db: Session, job_id: int, user_id: int) -> VideoJob:
    job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
    # Don't leak existence of another user's job: missing and not-owned both 404.
    if not job or job.user_id != user_id:
        raise NotFoundError("Job")
    return job


def list_jobs(db: Session, user_id: int) -> list[VideoJob]:
    return (
        db.query(VideoJob)
        .filter(VideoJob.user_id == user_id)
        .order_by(VideoJob.created_at.desc())
        .all()
    )


def delete_job(db: Session, job_id: int, user_id: int) -> None:
    job = get_job(db, job_id, user_id)
    if job.rq_job_id:
        from app.queue import cancel_pipeline

        cancel_pipeline(job.rq_job_id)
    db.delete(job)
    db.commit()
    logger.info("Deleted job id=%s for user_id=%s", job_id, user_id)
