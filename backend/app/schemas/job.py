from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.models.video_job import JobStatus, SourceType


class JobCreateURL(BaseModel):
    youtube_url: HttpUrl


class JobResponse(BaseModel):
    id: int
    user_id: int
    source_type: SourceType
    youtube_url: str | None
    uploaded_file_path: str | None
    source_title: str | None
    source_duration_seconds: int | None
    status: JobStatus
    error_message: str | None
    output_file_path: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
