"""
Detection & Results Management Routes for VisualGuard AI
=========================================================

Provides read-only API endpoints for querying detection data and
processed media results.

Endpoints:
  GET /api/results/media/{media_id}/entities              - List detected entities for a video
  GET /api/results/entities/{entity_id}                   - Get a single detected entity
  GET /api/results/entities/{entity_id}/detections        - List frame-level detections for an entity
  GET /api/results/detections/{detection_id}              - Get a single detection record
  GET /api/results/media/{media_id}/processed             - List processed media outputs for a video
  GET /api/results/processed/{processed_id}               - Get a single processed media record
  GET /api/results/processed/{processed_id}/selections    - List selected objects for a processed result
  GET /api/results/selections/{selection_id}              - Get a single selected object record
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.detected_entity import DetectedEntityListResponse, DetectedEntityResponse
from app.schemas.detection import DetectionListResponse, DetectionResponse
from app.schemas.processed_media import ProcessedMediaListResponse, ProcessedMediaResponse
from app.schemas.selected_object import SelectedObjectListResponse, SelectedObjectResponse
from app.services.results_service import (
    get_detection_by_id,
    get_detections_for_entity,
    get_entities_for_media,
    get_entity_by_id,
    get_processed_media_by_id,
    get_processed_media_for_media,
    get_selected_object_by_id,
    get_selected_objects_for_processed,
    media_exists,
)

router = APIRouter(prefix="/api/results", tags=["Detection & Results"])


# ---------------------------------------------------------------------------
# Detected Entities
# ---------------------------------------------------------------------------


@router.get(
    "/media/{media_id}/entities",
    response_model=DetectedEntityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List detected entities for a media record",
    description=(
        "Retrieve all detected entities (faces, licence plates, etc.) "
        "found in the specified media record. Supports pagination."
    ),
)
def list_entities_for_media(
    media_id: int,
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
) -> DetectedEntityListResponse:
    """
    Return detected entities associated with a given media_id.

    - Returns HTTP 404 if the media record does not exist.
    - Returns an empty list (total=0) if no entities have been detected yet.
    """
    if not media_exists(db, media_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media with id={media_id} not found.",
        )
    items, total = get_entities_for_media(db=db, media_id=media_id, skip=skip, limit=limit)
    return DetectedEntityListResponse(
        total=total,
        items=[DetectedEntityResponse.model_validate(e) for e in items],
    )


@router.get(
    "/entities/{entity_id}",
    response_model=DetectedEntityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a detected entity by ID",
    description="Retrieve full details of a single detected entity record.",
)
def get_entity(
    entity_id: int,
    db: Session = Depends(get_db),
) -> DetectedEntityResponse:
    """
    Return a single DetectedEntity by its primary key.

    - Returns HTTP 404 if no entity with the given ID exists.
    """
    entity = get_entity_by_id(db=db, entity_id=entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detected entity with id={entity_id} not found.",
        )
    return DetectedEntityResponse.model_validate(entity)


# ---------------------------------------------------------------------------
# Detections (frame-level bounding boxes)
# ---------------------------------------------------------------------------


@router.get(
    "/entities/{entity_id}/detections",
    response_model=DetectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List detections for a detected entity",
    description=(
        "Retrieve frame-level bounding-box detections for a given entity, "
        "ordered by frame number ascending. Supports pagination."
    ),
)
def list_detections_for_entity(
    entity_id: int,
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
) -> DetectionListResponse:
    """
    Return all frame-level detections linked to the given entity_id.

    - Returns HTTP 404 if the entity does not exist.
    - Returns an empty list if the entity has no detections yet.
    """
    if not get_entity_by_id(db=db, entity_id=entity_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detected entity with id={entity_id} not found.",
        )
    items, total = get_detections_for_entity(
        db=db, entity_id=entity_id, skip=skip, limit=limit
    )
    return DetectionListResponse(
        total=total,
        items=[DetectionResponse.model_validate(d) for d in items],
    )


@router.get(
    "/detections/{detection_id}",
    response_model=DetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a detection record by ID",
    description="Retrieve a single frame-level detection record including bounding-box coordinates.",
)
def get_detection(
    detection_id: int,
    db: Session = Depends(get_db),
) -> DetectionResponse:
    """
    Return a single Detection by its primary key.

    - Returns HTTP 404 if no detection with the given ID exists.
    """
    detection = get_detection_by_id(db=db, detection_id=detection_id)
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection with id={detection_id} not found.",
        )
    return DetectionResponse.model_validate(detection)


# ---------------------------------------------------------------------------
# Processed Media
# ---------------------------------------------------------------------------


@router.get(
    "/media/{media_id}/processed",
    response_model=ProcessedMediaListResponse,
    status_code=status.HTTP_200_OK,
    summary="List processed media outputs for a video",
    description=(
        "Retrieve all privacy-protected media outputs generated from the specified video. "
        "Supports pagination."
    ),
)
def list_processed_for_media(
    media_id: int,
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
) -> ProcessedMediaListResponse:
    """
    Return all processed media records associated with a given media_id.

    - Returns HTTP 404 if the media record does not exist.
    - Returns an empty list if no outputs have been generated yet.
    """
    if not media_exists(db, media_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media with id={media_id} not found.",
        )
    items, total = get_processed_media_for_media(
        db=db, media_id=media_id, skip=skip, limit=limit
    )
    return ProcessedMediaListResponse(
        total=total,
        items=[ProcessedMediaResponse.model_validate(p) for p in items],
    )


@router.get(
    "/processed/{processed_id}",
    response_model=ProcessedMediaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a processed media record by ID",
    description="Retrieve full details of a single processed media output.",
)
def get_processed(
    processed_id: int,
    db: Session = Depends(get_db),
) -> ProcessedMediaResponse:
    """
    Return a single ProcessedMedia record by its primary key.

    - Returns HTTP 404 if no processed record with the given ID exists.
    """
    processed = get_processed_media_by_id(db=db, processed_id=processed_id)
    if not processed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processed media with id={processed_id} not found.",
        )
    return ProcessedMediaResponse.model_validate(processed)


# ---------------------------------------------------------------------------
# Selected Objects
# ---------------------------------------------------------------------------


@router.get(
    "/processed/{processed_id}/selections",
    response_model=SelectedObjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List selected objects for a processed media result",
    description=(
        "Retrieve all user-selected objects (entities chosen for concealment) "
        "linked to a given processed media record. Supports pagination."
    ),
)
def list_selections_for_processed(
    processed_id: int,
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
) -> SelectedObjectListResponse:
    """
    Return all selected objects linked to the given processed_id.

    - Returns HTTP 404 if the processed media record does not exist.
    - Returns an empty list if no objects have been selected yet.
    """
    if not get_processed_media_by_id(db=db, processed_id=processed_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processed media with id={processed_id} not found.",
        )
    items, total = get_selected_objects_for_processed(
        db=db, processed_id=processed_id, skip=skip, limit=limit
    )
    return SelectedObjectListResponse(
        total=total,
        items=[SelectedObjectResponse.model_validate(s) for s in items],
    )


@router.get(
    "/selections/{selection_id}",
    response_model=SelectedObjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a selected object record by ID",
    description="Retrieve a single selected object record including concealment type and intensity.",
)
def get_selection(
    selection_id: int,
    db: Session = Depends(get_db),
) -> SelectedObjectResponse:
    """
    Return a single SelectedObject by its primary key.

    - Returns HTTP 404 if no selection with the given ID exists.
    """
    selection = get_selected_object_by_id(db=db, selection_id=selection_id)
    if not selection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selected object with id={selection_id} not found.",
        )
    return SelectedObjectResponse.model_validate(selection)

