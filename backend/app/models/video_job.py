import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Enum,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin


class SourceType(enum.Enum):
    youtube_url = "youtube_url"
    upload = "upload"


class JobStatus(enum.Enum):
    queued = "queued"
    downloading = "downloading"
    transcribing = "transcribing"
    analyzing = "analyzing"
    rendering = "rendering"
    done = "done"
    failed = "failed"


class VideoJob(Base, TimestampMixin):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type = Column(Enum(SourceType), nullable=False)
    youtube_url = Column(String(1000), nullable=True)
    uploaded_file_path = Column(String(1000), nullable=True)
    source_title = Column(String(500), nullable=True)
    source_duration_seconds = Column(Integer, nullable=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.queued, index=True)
    error_message = Column(Text, nullable=True)
    output_file_path = Column(String(1000), nullable=True)

    # Relationships
    user = relationship("User", back_populates="video_jobs")
    transcript_segments = relationship(
        "TranscriptSegment", back_populates="job", cascade="all, delete-orphan"
    )
    selected_moments = relationship(
        "SelectedMoment", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_video_jobs_user_status", "user_id", "status"),
    )
