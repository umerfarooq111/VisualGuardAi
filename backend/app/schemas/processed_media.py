"""
Pydantic schemas for PROCESSED_MEDIA records.

Covers both read-only results (used by results_service) and the
processed-output management endpoints (save, list, retrieve, delete).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base / existing schemas (unchanged — keep existing consumers working)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Upload / save schemas  (new — for the processed-output management API)
# ---------------------------------------------------------------------------

ALLOWED_OUTPUT_TYPES = {"protected_video", "faces_blurred", "plates_blurred", "both_blurred"}


class ProcessedOutputSaveRequest(BaseModel):
    """
    Request body for POST /api/outputs/save.

    The AI pipeline calls this endpoint after completing video processing.
    It supplies the task_id so the backend can derive media_id automatically.
    output_type describes what protection was applied.
    """

    task_id: int = Field(..., gt=0, description="Processing task that produced this output")
    output_type: Literal[
        "protected_video", "faces_blurred", "plates_blurred", "both_blurred"
    ] = Field(
        default="protected_video",
        description="Type of protection applied to this output",
    )


class ProcessedOutputSaveResponse(BaseModel):
    """
    Response after successfully registering a processed output.
    """

    processed_id: int
    media_id: int
    task_id: int
    filename: str
    output_path: str
    output_type: str
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(default="saved")

