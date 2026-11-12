"""
Detection & Results Service Layer for VisualGuard AI
=====================================================

Handles read operations for:
- DetectedEntity  (DETECTED_ENTITY table)
- Detection       (DETECTION table)
- ProcessedMedia  (PROCESSED_MEDIA table)
- SelectedObject  (SELECTED_OBJECT table)

No write operations are performed here — this module retrieves existing
records created by the AI processing pipeline.
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.detected_entity import DetectedEntity
from app.models.detection import Detection
from app.models.media import Media
from app.models.processed_media import ProcessedMedia
from app.models.selected_object import SelectedObject


# ---------------------------------------------------------------------------
# Media existence helper
# ---------------------------------------------------------------------------


def media_exists(db: Session, media_id: int) -> bool:
    """Return True if a Media record with the given ID exists."""
    return db.query(Media.media_id).filter(Media.media_id == media_id).scalar() is not None


# ---------------------------------------------------------------------------
# DetectedEntity queries
# ---------------------------------------------------------------------------


def get_entities_for_media(
    db: Session,
    media_id: int,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[DetectedEntity], int]:
    """
    Retrieve a paginated list of detected entities for a given media record.

    Returns:
        Tuple[List[DetectedEntity], int]: (entity list, total count)
    """
    query = db.query(DetectedEntity).filter(DetectedEntity.media_id == media_id)
    total = query.count()
    items = query.order_by(DetectedEntity.entity_id.asc()).offset(skip).limit(limit).all()
    return items, total


def get_entity_by_id(db: Session, entity_id: int) -> Optional[DetectedEntity]:
    """
    Retrieve a single DetectedEntity by its primary key.

    Returns:
        DetectedEntity | None
    """
    return (
        db.query(DetectedEntity)
        .filter(DetectedEntity.entity_id == entity_id)
        .first()
    )


# ---------------------------------------------------------------------------
# Detection queries
# ---------------------------------------------------------------------------


def get_detections_for_entity(
    db: Session,
    entity_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[Detection], int]:
    """
    Retrieve a paginated list of frame-level detections for a given entity.

    Returns:
        Tuple[List[Detection], int]: (detection list, total count)
    """
    query = db.query(Detection).filter(Detection.entity_id == entity_id)
    total = query.count()
    items = (
        query.order_by(Detection.frame_number.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_detection_by_id(db: Session, detection_id: int) -> Optional[Detection]:
    """
    Retrieve a single Detection record by its primary key.

    Returns:
        Detection | None
    """
    return (
        db.query(Detection)
        .filter(Detection.detection_id == detection_id)
        .first()
    )


# ---------------------------------------------------------------------------
# ProcessedMedia queries
# ---------------------------------------------------------------------------


def get_processed_media_for_media(
    db: Session,
    media_id: int,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[ProcessedMedia], int]:
    """
    Retrieve all processed media records associated with a given media ID.

    Returns:
        Tuple[List[ProcessedMedia], int]: (processed media list, total count)
    """
    query = db.query(ProcessedMedia).filter(ProcessedMedia.media_id == media_id)
    total = query.count()
    items = (
        query.order_by(ProcessedMedia.processed_id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_processed_media_by_id(
    db: Session, processed_id: int
) -> Optional[ProcessedMedia]:
    """
    Retrieve a single ProcessedMedia record by its primary key.

    Returns:
        ProcessedMedia | None
    """
    return (
        db.query(ProcessedMedia)
        .filter(ProcessedMedia.processed_id == processed_id)
        .first()
    )


# ---------------------------------------------------------------------------
# SelectedObject queries
# ---------------------------------------------------------------------------


def get_selected_objects_for_processed(
    db: Session,
    processed_id: int,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[SelectedObject], int]:
    """
    Retrieve all selected objects linked to a given processed media record.

    Returns:
        Tuple[List[SelectedObject], int]: (selected object list, total count)
    """
    query = db.query(SelectedObject).filter(
        SelectedObject.processed_id == processed_id
    )
    total = query.count()
    items = (
        query.order_by(SelectedObject.selection_id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_selected_object_by_id(
    db: Session, selection_id: int
) -> Optional[SelectedObject]:
    """
    Retrieve a single SelectedObject record by its primary key.

    Returns:
        SelectedObject | None
    """
    return (
        db.query(SelectedObject)
        .filter(SelectedObject.selection_id == selection_id)
        .first()
    )

