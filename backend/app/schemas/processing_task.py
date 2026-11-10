"""
Pydantic schemas for ProcessingTask request/response serialization.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProcessingTaskCreate(BaseModel):
    """
    Schema for creating a new processing task.

    Validates media_id, protection_type, and optional blur_intensity.
    """

    media_id: int = Field(..., gt=0, description="ID of the media to process")
    protection_type: Literal["faces", "number_plates", "both"] = Field(
        ..., description="Type of object to protect: faces, number_plates, or both"
    )
    blur_intensity: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Blur intensity between 0 and 100 (optional)",
    )


class ProcessingTaskResponse(BaseModel):
    """
    Schema for returning a single processing task record.
    """

    model_config = ConfigDict(from_attributes=True)

    task_id: int
    media_id: int
    status: str
    progress: Optional[float]
    protection_type: str
    blur_intensity: Optional[float]
    error_message: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class ProcessingTaskListResponse(BaseModel):
    """
    Schema for a paginated list of processing tasks.
    """

    total: int = Field(..., description="Total number of processing tasks")
    items: List[ProcessingTaskResponse] = Field(
        ..., description="List of processing task records"
    )

