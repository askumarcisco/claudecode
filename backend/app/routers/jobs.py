import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.exceptions import ValidationError
from app.models.user import User
from app.models.video_job import JobStatus, VideoJob
from app.queue import enqueue_pipeline
from app.schemas.job import JobResponse
from app.services import job_service, upload_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    youtube_url: str | None = Form(None),
    file: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoJob:
    has_url = youtube_url is not None and youtube_url.strip() != ""
    has_file = file is not None and file.filename

    if has_url and has_file:
        raise ValidationError("Provide either youtube_url or file, not both")
    if not has_url and not has_file:
        raise ValidationError("Either youtube_url or file must be provided")

    if has_url:
        job = job_service.create_job_from_url(db, user.id, youtube_url)
    else:
        saved_path = await upload_service.save_upload(file, job_id_hint="new")
        job = job_service.create_job_from_upload(db, user.id, saved_path)

    # Runs in a separate worker process (see app/queue.py) rather than a
    # FastAPI BackgroundTask, so a crashed/killed job can't take the API
    # process down with it.
    job.rq_job_id = enqueue_pipeline(job.id)
    db.commit()
    db.refresh(job)
    logger.info("Scheduled pipeline run for job id=%s (rq_job_id=%s)", job.id, job.rq_job_id)

    return job


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VideoJob]:
    return job_service.list_jobs(db, user.id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoJob:
    return job_service.get_job(db, job_id, user.id)


@router.get("/{job_id}/download")
async def download_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    job = job_service.get_job(db, job_id, user.id)
    if job.status != JobStatus.done or not job.output_file_path:
        raise ValidationError("Job output is not available for download")

    filename = f"job_{job.id}.mp4"
    return FileResponse(
        path=job.output_file_path,
        media_type="video/mp4",
        filename=filename,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    job_service.delete_job(db, job_id, user.id)
    return None
