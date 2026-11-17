"""
Pydantic schemas for ProcessingTask request/response serialization.

Also contains schemas for the detection ingestion endpoint:
  POST /api/processing/tasks/{task_id}/detections
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


# ---------------------------------------------------------------------------
# Task Lifecycle Management schemas (Phase 6)
# ---------------------------------------------------------------------------


class TaskProgressUpdate(BaseModel):
    """
    Request body for updating processing task progress.
    Validates that progress is a percentage between 0.0 and 100.0.
    """

    progress: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Task progress percentage (0.0 to 100.0)",
    )


class TaskFailRequest(BaseModel):
    """
    Request body for marking a processing task as failed.
    Requires a non-empty error message.
    """

    error_message: str = Field(
        ...,
        min_length=1,
        description="Error message explaining why the task failed",
    )


# ---------------------------------------------------------------------------
# Detection ingestion schemas
# ---------------------------------------------------------------------------

# Allowed entity types accepted by the ingestion endpoint
ALLOWED_ENTITY_TYPES = {"face", "number_plate"}


class DetectionIngestionItem(BaseModel):
    """
    A single detection event from the AI pipeline.

    Represents one entity instance detected on one video frame.
    confidence is intentionally absent — the pipeline does not supply it
    and DETECTION.confidence is nullable, so NULL will be stored.
    """

    tracking_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Stable tracking identifier for this entity across frames",
    )
    entity_type: Literal["face", "number_plate"] = Field(
        ...,
        description="Type of detected entity: 'face' or 'number_plate'",
    )
    frame_number: int = Field(
        ...,
        ge=0,
        description="Zero-based video frame index where this detection occurs",
    )
    timestamp: float = Field(
        ...,
        ge=0.0,
        description="Time offset in seconds from the start of the video",
    )
    bbox_x: float = Field(
        ...,
        ge=0.0,
        description="Bounding box left-edge X coordinate (pixels)",
    )
    bbox_y: float = Field(
        ...,
        ge=0.0,
        description="Bounding box top-edge Y coordinate (pixels)",
    )
    bbox_width: float = Field(
        ...,
        gt=0.0,
        description="Bounding box width in pixels (must be > 0)",
    )
    bbox_height: float = Field(
        ...,
        gt=0.0,
        description="Bounding box height in pixels (must be > 0)",
    )


class DetectionIngestionRequest(BaseModel):
    """
    Request body for POST /api/processing/tasks/{task_id}/detections.

    Contains one or more detection events to persist atomically.
    """

    detections: List[DetectionIngestionItem] = Field(
        ...,
        min_length=1,
        description="One or more detection events to ingest",
    )


class SavedDetectionDetail(BaseModel):
    """
    Details of a single saved Detection row, returned inside the ingestion response.
    """

    model_config = ConfigDict(from_attributes=True)

    detection_id: int
    entity_id: int
    tracking_id: str
    entity_type: str
    frame_number: int
    timestamp: float
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    confidence: Optional[float] = None


class DetectionIngestionResponse(BaseModel):
    """
    Response for a successful detection ingestion request.
    """

    task_id: int = Field(..., description="Processing task ID")
    media_id: int = Field(..., description="Media ID associated with the task")
    entities_created: int = Field(..., description="Number of new DetectedEntity rows created")
    entities_reused: int = Field(..., description="Number of existing DetectedEntity rows reused")
    detections_saved: int = Field(..., description="Total Detection rows inserted")
    detections: List[SavedDetectionDetail] = Field(
        ..., description="Details of each saved detection"
    )

