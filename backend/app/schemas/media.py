"""
Pydantic schemas for Media records and video upload response serialization.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MediaBase(BaseModel):
    """Base schema for Media entity."""

    user_id: int = Field(default=1, description="ID of the user who owns this media")
    file_name: Optional[str] = Field(None, description="Original filename of the media")
    file_path: Optional[str] = Field(None, description="Local storage file path relative to backend")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")
    fps: Optional[float] = Field(None, description="Frames per second")


class MediaCreate(MediaBase):
    """Schema for creating a Media record."""

    file_name: str
    file_path: str


class MediaResponse(MediaBase):
    """Public representation of a Media record."""

    media_id: int = Field(..., description="Unique media database ID")

    model_config = ConfigDict(from_attributes=True)


class MediaMetadata(BaseModel):
    """Technical metadata extracted via OpenCV."""

    duration_seconds: Optional[float] = Field(None, description="Video duration in seconds")
    fps: Optional[float] = Field(None, description="Video frame rate (FPS)")
    width: Optional[int] = Field(None, description="Frame width in pixels")
    height: Optional[int] = Field(None, description="Frame height in pixels")
    file_size: int = Field(..., description="File size in bytes")


class MediaUploadResponse(BaseModel):
    """Structured response returned upon successful media upload."""

    media_id: int = Field(..., description="Unique media database ID")
    user_id: int = Field(..., description="Owner user ID")
    file_name: str = Field(..., description="Original name of the uploaded media")
    file_path: str = Field(..., description="Local filesystem path")
    status: str = Field(default="uploaded", description="Upload status")
    metadata: MediaMetadata = Field(..., description="Extracted video metadata")

    model_config = ConfigDict(from_attributes=True)


class MediaListResponse(BaseModel):
    """Paginated list of Media records."""

    total: int = Field(..., description="Total count of media items")
    items: List[MediaResponse] = Field(..., description="List of media items")

