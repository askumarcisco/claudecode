"""Orchestrates the full video-to-summary processing pipeline.

Entry point `run_pipeline(job_id)` is invoked as a FastAPI BackgroundTask
by the jobs router after a VideoJob row is created. It owns its own DB
session (background tasks have no request-scoped session available) and
must never let an exception escape — FastAPI silently swallows exceptions
raised inside a BackgroundTask, so any failure must be caught here and
persisted onto the job row instead.
"""

import logging
import os

from app.config import settings
from app.database import SessionLocal
from app.models.selected_moment import SelectedMoment
from app.models.transcript_segment import TranscriptSegment
from app.models.video_job import JobStatus, SourceType, VideoJob
from app.services import analysis_service, download_service, render_service, transcription_service

logger = logging.getLogger(__name__)

TARGET_SUMMARY_DURATION_SECONDS = 60


def run_pipeline(job_id: int) -> None:
    """Run the full pipeline for `job_id`: download -> transcribe ->
    analyze -> render. Updates job.status at each step and never raises.
    """
    db = SessionLocal()
    try:
        job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
        if job is None:
            logger.error("run_pipeline: job_id=%s not found", job_id)
            return

        try:
            _run_download_step(db, job)
            _run_transcription_step(db, job)
            _run_analysis_step(db, job)
            _run_rendering_step(db, job)

            job.status = JobStatus.done
            db.commit()
            logger.info("Pipeline completed for job_id=%s", job_id)
        except Exception as e:  # noqa: BLE001 - must never let an exception escape
            logger.exception("Pipeline failed for job_id=%s", job_id)
            db.rollback()
            # Re-fetch in case the failed transaction invalidated the instance.
            job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
            if job is not None:
                job.status = JobStatus.failed
                job.error_message = str(e)[:2000]
                db.commit()
    finally:
        db.close()


def _run_download_step(db, job: VideoJob) -> None:
    job.status = JobStatus.downloading
    db.commit()

    download_dir = os.path.join(settings.UPLOAD_DIR, f"job_{job.id}")

    if job.source_type == SourceType.youtube_url:
        file_path, title, duration_seconds = download_service.download_youtube_video(
            job.youtube_url, download_dir
        )
        job.uploaded_file_path = file_path
    else:
        title, duration_seconds = download_service.get_local_video_info(job.uploaded_file_path)

    job.source_title = title
    job.source_duration_seconds = duration_seconds
    db.commit()


def _run_transcription_step(db, job: VideoJob) -> None:
    job.status = JobStatus.transcribing
    db.commit()

    audio_dir = os.path.join(settings.UPLOAD_DIR, f"job_{job.id}")
    audio_path = transcription_service.extract_audio(job.uploaded_file_path, audio_dir)
    segments = transcription_service.transcribe_audio(audio_path, settings.WHISPER_MODEL)

    for seg in segments:
        db.add(
            TranscriptSegment(
                job_id=job.id,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"],
            )
        )
    db.commit()


def _run_analysis_step(db, job: VideoJob) -> None:
    job.status = JobStatus.analyzing
    db.commit()

    transcript_segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.job_id == job.id)
        .order_by(TranscriptSegment.start_time)
        .all()
    )
    segment_dicts = [
        {"start": seg.start_time, "end": seg.end_time, "text": seg.text}
        for seg in transcript_segments
    ]

    moments = analysis_service.select_key_moments(
        segment_dicts, target_duration_seconds=TARGET_SUMMARY_DURATION_SECONDS
    )

    for moment in moments:
        db.add(
            SelectedMoment(
                job_id=job.id,
                start_time=moment["start"],
                end_time=moment["end"],
                reason=moment.get("reason"),
            )
        )
    db.commit()


def _run_rendering_step(db, job: VideoJob) -> None:
    job.status = JobStatus.rendering
    db.commit()

    moments = (
        db.query(SelectedMoment)
        .filter(SelectedMoment.job_id == job.id)
        .order_by(SelectedMoment.start_time)
        .all()
    )
    moment_dicts = [{"start": m.start_time, "end": m.end_time} for m in moments]

    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(settings.OUTPUT_DIR, f"{job.id}.mp4")

    render_service.render_summary(job.uploaded_file_path, moment_dicts, output_path)

    job.output_file_path = output_path
    db.commit()
