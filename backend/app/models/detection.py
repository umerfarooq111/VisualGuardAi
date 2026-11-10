"""
SQLAlchemy model representing individual frame-level bounding box detections.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base


class Detection(Base):
    """
    DETECTION entity representing a single bounding box detection on a specific video frame.
    """

    __tablename__ = "DETECTION"

    detection_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entity_id = Column(
        Integer, ForeignKey("DETECTED_ENTITY.entity_id", ondelete="CASCADE"), nullable=False, index=True
    )
    frame_number = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    timestamp = Column(Float, nullable=True)
    bbox_x = Column(Float, nullable=True)
    bbox_y = Column(Float, nullable=True)
    bbox_width = Column(Float, nullable=True)
    bbox_height = Column(Float, nullable=True)

    # Relationships
    entity = relationship("DetectedEntity", back_populates="detections")

    def __repr__(self) -> str:
        return f"<Detection(detection_id={self.detection_id}, entity_id={self.entity_id}, frame={self.frame_number})>"

