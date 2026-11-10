"""
SQLAlchemy model representing distinct detected/tracked visual entities.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class DetectedEntity(Base):
    """
    DETECTED_ENTITY represents an individual object (e.g. specific face or license plate)
    tracked across multiple video frames.
    """

    __tablename__ = "DETECTED_ENTITY"

    entity_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey("Media.media_id", ondelete="CASCADE"), nullable=False, index=True)
    tracking_id = Column(String(100), nullable=True)
    entity_type = Column(String(100), nullable=True)

    # Relationships
    media = relationship("Media", back_populates="detected_entities")
    detections = relationship("Detection", back_populates="entity", cascade="all, delete-orphan")
    selected_objects = relationship(
        "SelectedObject", back_populates="entity", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DetectedEntity(entity_id={self.entity_id}, tracking_id='{self.tracking_id}', entity_type='{self.entity_type}')>"

