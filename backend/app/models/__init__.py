"""
Database models package for VisualGuard AI.
Implements the official FYP database schema.
"""

from app.database import Base
from app.models.detected_entity import DetectedEntity
from app.models.detection import Detection
from app.models.media import Media
from app.models.processed_media import ProcessedMedia
from app.models.selected_object import SelectedObject
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Media",
    "ProcessedMedia",
    "DetectedEntity",
    "Detection",
    "SelectedObject",
]
