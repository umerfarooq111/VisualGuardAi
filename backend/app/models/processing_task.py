"""
SQLAlchemy model for the PROCESSING_TASK table.

Tracks video processing jobs, their status, progress, and configuration.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Double, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ProcessingTask(Base):
    """ORM model mapped to the existing PROCESSING_TASK PostgreSQL table."""

    __tablename__ = "PROCESSING_TASK"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(
        Integer,
        ForeignKey("Media.media_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Double, nullable=True, default=0.0)
    protection_type = Column(String(50), nullable=False)
    blur_intensity = Column(Double, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship back to Media
    media = relationship("Media", back_populates="processing_tasks")

