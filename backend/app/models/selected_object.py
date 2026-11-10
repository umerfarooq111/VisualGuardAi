"""
SQLAlchemy model representing user-selected objects for privacy concealment.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class SelectedObject(Base):
    """
    SELECTED_OBJECT represents an entity chosen by the user for concealing (blur/pixelate/etc.)
    and linked to a processed media output.
    """

    __tablename__ = "SELECTED_OBJECT"

    selection_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    object_id = Column(
        Integer, ForeignKey("DETECTED_ENTITY.entity_id", ondelete="CASCADE"), nullable=False, index=True
    )
    processed_id = Column(
        Integer, ForeignKey("PROCESSED_MEDIA.processed_id", ondelete="CASCADE"), nullable=False, index=True
    )
    concealing_type = Column("Concealing_Type", String(100), nullable=True)
    intensity = Column(Float, nullable=True)

    # Relationships
    entity = relationship("DetectedEntity", back_populates="selected_objects")
    processed_media = relationship("ProcessedMedia", back_populates="selected_objects")

    def __repr__(self) -> str:
        return f"<SelectedObject(selection_id={self.selection_id}, object_id={self.object_id}, concealing_type='{self.concealing_type}')>"

