"""
Pydantic schemas package for request/response serialization.
Implements schemas for the official FYP models.
"""

from app.schemas.detected_entity import (
    DetectedEntityBase,
    DetectedEntityCreate,
    DetectedEntityListResponse,
    DetectedEntityResponse,
)
from app.schemas.detection import (
    DetectionBase,
    DetectionCreate,
    DetectionListResponse,
    DetectionResponse,
)
from app.schemas.health import AppInfoResponse, DatabaseHealth, HealthResponse
from app.schemas.media import (
    MediaBase,
    MediaCreate,
    MediaListResponse,
    MediaMetadata,
    MediaResponse,
    MediaUploadResponse,
)
from app.schemas.processed_media import (
    ProcessedMediaBase,
    ProcessedMediaCreate,
    ProcessedMediaListResponse,
    ProcessedMediaResponse,
)
from app.schemas.selected_object import (
    SelectedObjectBase,
    SelectedObjectCreate,
    SelectedObjectListResponse,
    SelectedObjectResponse,
)

__all__ = [
    "AppInfoResponse",
    "DatabaseHealth",
    "HealthResponse",
    "MediaBase",
    "MediaCreate",
    "MediaResponse",
    "MediaMetadata",
    "MediaUploadResponse",
    "MediaListResponse",
    "ProcessedMediaBase",
    "ProcessedMediaCreate",
    "ProcessedMediaResponse",
    "ProcessedMediaListResponse",
    "DetectedEntityBase",
    "DetectedEntityCreate",
    "DetectedEntityResponse",
    "DetectedEntityListResponse",
    "DetectionBase",
    "DetectionCreate",
    "DetectionResponse",
    "DetectionListResponse",
    "SelectedObjectBase",
    "SelectedObjectCreate",
    "SelectedObjectResponse",
    "SelectedObjectListResponse",
]
