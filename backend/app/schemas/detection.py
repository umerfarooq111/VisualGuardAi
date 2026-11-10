"""
Pydantic schemas for DETECTION records (frame-level bounding boxes).
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DetectionBase(BaseModel):
    """Base schema for frame-level bounding box detection."""

    entity_id: int = Field(..., description="Referenced entity ID")
    frame_number: Optional[int] = Field(None, description="Video frame number")
    confidence: Optional[float] = Field(None, description="Detection confidence score (0.0 - 1.0)")
    timestamp: Optional[float] = Field(None, description="Timestamp in seconds")
    bbox_x: Optional[float] = Field(None, description="Bounding box X coordinate")
    bbox_y: Optional[float] = Field(None, description="Bounding box Y coordinate")
    bbox_width: Optional[float] = Field(None, description="Bounding box width")
    bbox_height: Optional[float] = Field(None, description="Bounding box height")


class DetectionCreate(DetectionBase):
    """Schema for creating a detection record."""

    pass


class DetectionResponse(DetectionBase):
    """Public representation of a detection record."""

    detection_id: int = Field(..., description="Unique detection ID")

    model_config = ConfigDict(from_attributes=True)


class DetectionListResponse(BaseModel):
    """List response for detection records."""

    total: int = Field(..., description="Total count")
    items: List[DetectionResponse] = Field(..., description="List of detections")

