"""
SQLAlchemy model representing uploaded media (video/audio) files.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Media(Base):
    """
    Media entity representing an uploaded video file.
    """

    __tablename__ = "Media"

    media_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("User.user_id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(255), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="media_items")
    processed_media_items = relationship("ProcessedMedia", back_populates="media", cascade="all, delete-orphan")
    detected_entities = relationship("DetectedEntity", back_populates="media", cascade="all, delete-orphan")
    processing_tasks = relationship("ProcessingTask", back_populates="media", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Media(media_id={self.media_id}, file_name='{self.file_name}', user_id={self.user_id})>"

