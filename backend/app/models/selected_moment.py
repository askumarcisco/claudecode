from sqlalchemy import Column, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SelectedMoment(Base):
    __tablename__ = "selected_moments"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer, ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)

    # Relationships
    job = relationship("VideoJob", back_populates="selected_moments")
