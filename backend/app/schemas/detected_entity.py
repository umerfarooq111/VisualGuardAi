"""
Pydantic schemas for DETECTED_ENTITY records.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DetectedEntityBase(BaseModel):
    """Base schema for DETECTED_ENTITY."""

    media_id: int = Field(..., description="Referenced media ID")
    tracking_id: Optional[str] = Field(None, description="Tracking identifier across frames")
    entity_type: Optional[str] = Field(None, description="Type of entity (e.g. 'face', 'license_plate')")


class DetectedEntityCreate(DetectedEntityBase):
    """Schema for creating a detected entity."""

    pass


class DetectedEntityResponse(DetectedEntityBase):
    """Public representation of a detected entity."""

    entity_id: int = Field(..., description="Unique entity ID")

    model_config = ConfigDict(from_attributes=True)


class DetectedEntityListResponse(BaseModel):
    """List response for detected entities."""

    total: int = Field(..., description="Total count")
    items: List[DetectedEntityResponse] = Field(..., description="List of detected entities")

