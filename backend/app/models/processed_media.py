"""
SQLAlchemy model representing processed media outputs.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class ProcessedMedia(Base):
    """
    PROCESSED_MEDIA entity representing privacy-protected media outputs.
    """

    __tablename__ = "PROCESSED_MEDIA"

    processed_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey("Media.media_id", ondelete="CASCADE"), nullable=False, index=True)
    output_path = Column(String(255), nullable=True)
    output_type = Column(String(100), nullable=True)

    # Relationships
    media = relationship("Media", back_populates="processed_media_items")
    selected_objects = relationship(
        "SelectedObject", back_populates="processed_media", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProcessedMedia(processed_id={self.processed_id}, media_id={self.media_id}, output_type='{self.output_type}')>"

