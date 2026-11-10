"""
Pydantic schemas for PROCESSED_MEDIA records.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProcessedMediaBase(BaseModel):
    """Base schema for PROCESSED_MEDIA."""

    media_id: int = Field(..., description="Referenced media ID")
    output_path: Optional[str] = Field(None, description="Filesystem path to processed video")
    output_type: Optional[str] = Field(None, description="Type/format of processed output")


class ProcessedMediaCreate(ProcessedMediaBase):
    """Schema for creating a processed media record."""

    output_path: str
    output_type: str = "protected_video"


class ProcessedMediaResponse(ProcessedMediaBase):
    """Public representation of a processed media record."""

    processed_id: int = Field(..., description="Unique processed media ID")

    model_config = ConfigDict(from_attributes=True)


class ProcessedMediaListResponse(BaseModel):
    """List response for processed media records."""

    total: int = Field(..., description="Total count")
    items: List[ProcessedMediaResponse] = Field(..., description="Processed media records")

