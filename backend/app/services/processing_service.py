"""
Processing Service Layer for VisualGuard AI
============================================

Handles:
- Creating processing task records in the PROCESSING_TASK table.
- Validating that the referenced media exists.
- Retrieving single tasks and paginated task lists.
- Lifecycle management: starting tasks, updating progress, failure handling.
- Ingesting AI detection results into DETECTED_ENTITY and DETECTION tables.
"""

from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.detected_entity import DetectedEntity
from app.models.detection import Detection
from app.models.media import Media
from app.models.processing_task import ProcessingTask


def get_media_or_404(db: Session, media_id: int) -> Media:
    """
    Retrieve a Media record by primary key.

    Raises:
        HTTPException (404): If the media record does not exist.
    """
    media = db.query(Media).filter(Media.media_id == media_id).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media with id={media_id} not found.",
        )
    return media


def create_processing_task(
    db: Session,
    media_id: int,
    protection_type: str,
    blur_intensity: Optional[float],
) -> ProcessingTask:
    """
    Create a new processing task record.

    Validates that the referenced media exists, then inserts a new
    ProcessingTask row with status='pending' and progress=0.

    Returns:
        ProcessingTask: The newly created ORM instance.

    Raises:
        HTTPException (404): If media_id does not exist.
        HTTPException (500): On database failure.
    """
    # Confirm referenced media exists
    get_media_or_404(db, media_id)

    task = ProcessingTask(
        media_id=media_id,
        protection_type=protection_type,
        blur_intensity=blur_intensity,
        status="pending",
        progress=0.0,
    )

    try:
        db.add(task)
        db.commit()
        db.refresh(task)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while creating processing task: {str(exc)}",
        )

    return task


def get_task_by_id(db: Session, task_id: int) -> Optional[ProcessingTask]:
    """
    Retrieve a single processing task by its primary key.

    Returns:
        ProcessingTask | None
    """
    return (
        db.query(ProcessingTask)
        .filter(ProcessingTask.task_id == task_id)
        .first()
    )


def get_tasks_list(
    db: Session,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[ProcessingTask], int]:
    """
    Retrieve a paginated list of processing tasks ordered by newest first.

    Returns:
        Tuple[List[ProcessingTask], int]: (task list, total count)
    """
    query = db.query(ProcessingTask)
    total = query.count()
    items = (
        query.order_by(desc(ProcessingTask.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_task_or_404(db: Session, task_id: int) -> ProcessingTask:
    """
    Retrieve a processing task by its primary key, raising HTTP 404 if missing.
    """
    task = get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing task with id={task_id} not found.",
        )
    return task


# ---------------------------------------------------------------------------
# Task Lifecycle Management (Phase 6)
# ---------------------------------------------------------------------------


def start_processing_task(db: Session, task_id: int) -> ProcessingTask:
    """
    Start a pending processing task by updating its status to 'processing'.

    Prevents starting tasks that are already 'processing', 'completed', or 'failed'.

    Raises:
        HTTPException (404): If task not found.
        HTTPException (400): If task is not in 'pending' status.
        HTTPException (500): On database error.
    """
    task = get_task_or_404(db, task_id)
    if task.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start task with id={task_id} because its current status is '{task.status}'. Only 'pending' tasks can be started.",
        )

    task.status = "processing"
    try:
        db.commit()
        db.refresh(task)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while starting processing task: {str(exc)}",
        )
    return task


def update_task_progress(db: Session, task_id: int, progress: float) -> ProcessingTask:
    """
    Update the progress (0.0 - 100.0) of a processing task.

    Prevents updating progress for tasks that are already 'completed' or 'failed'.

    Raises:
        HTTPException (404): If task not found.
        HTTPException (400): If task is already completed or failed.
        HTTPException (500): On database error.
    """
    task = get_task_or_404(db, task_id)
    if task.status in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update progress for task with id={task_id} because its status is '{task.status}'.",
        )

    task.progress = progress
    try:
        db.commit()
        db.refresh(task)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while updating task progress: {str(exc)}",
        )
    return task


def fail_processing_task(db: Session, task_id: int, error_message: str) -> ProcessingTask:
    """
    Mark a processing task as 'failed' and record the error message.

    Prevents failing a task that is already completed or already failed.

    Raises:
        HTTPException (404): If task not found.
        HTTPException (400): If task is already completed or failed.
        HTTPException (500): On database error.
    """
    task = get_task_or_404(db, task_id)
    if task.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot mark task with id={task_id} as failed because it is already completed.",
        )
    if task.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with id={task_id} is already marked as failed.",
        )

    task.status = "failed"
    task.error_message = error_message
    try:
        db.commit()
        db.refresh(task)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while marking task as failed: {str(exc)}",
        )
    return task


# ---------------------------------------------------------------------------
# Detection ingestion
# ---------------------------------------------------------------------------


def ingest_detections(
    db: Session,
    task: ProcessingTask,
    detection_items: List,
) -> Dict:
    """
    Atomically persist detected entities and their frame-level detection records.

    Strategy for entity de-duplication:
      - Within this request a cache keyed on (tracking_id, entity_type) is
        maintained so the same entity is not inserted twice.
      - Before inserting, existing DetectedEntity rows for the same
        (media_id, tracking_id, entity_type) are looked up in the database.
        If found they are reused; otherwise a new row is created.

    confidence is always stored as NULL because the AI pipeline does not
    supply it and DETECTION.confidence is nullable.

    All inserts happen inside a single transaction. On any SQLAlchemy error
    the entire transaction is rolled back so no partial records are left.

    Returns:
        Dict with keys: entities_created, entities_reused, detections_saved,
                        saved_detection_details (list of dicts)

    Raises:
        HTTPException (500): On database failure.
    """
    media_id: int = task.media_id

    # In-request entity cache: (tracking_id, entity_type) -> DetectedEntity ORM obj
    entity_cache: Dict[tuple, DetectedEntity] = {}
    entities_created = 0
    entities_reused = 0
    new_detections: List[Detection] = []

    try:
        for item in detection_items:
            cache_key = (item.tracking_id, item.entity_type)

            if cache_key in entity_cache:
                entity = entity_cache[cache_key]
            else:
                # Check if entity already exists in DB for this media
                entity = (
                    db.query(DetectedEntity)
                    .filter(
                        DetectedEntity.media_id == media_id,
                        DetectedEntity.tracking_id == item.tracking_id,
                        DetectedEntity.entity_type == item.entity_type,
                    )
                    .first()
                )
                if entity:
                    entities_reused += 1
                else:
                    entity = DetectedEntity(
                        media_id=media_id,
                        tracking_id=item.tracking_id,
                        entity_type=item.entity_type,
                    )
                    db.add(entity)
                    db.flush()   # get entity_id without committing
                    entities_created += 1

                entity_cache[cache_key] = entity

            detection = Detection(
                entity_id=entity.entity_id,
                frame_number=item.frame_number,
                confidence=None,   # pipeline does not supply confidence
                timestamp=item.timestamp,
                bbox_x=item.bbox_x,
                bbox_y=item.bbox_y,
                bbox_width=item.bbox_width,
                bbox_height=item.bbox_height,
            )
            db.add(detection)
            new_detections.append((detection, entity))

        db.commit()

        # Refresh to get auto-generated detection_ids
        saved_details = []
        for detection, entity in new_detections:
            db.refresh(detection)
            saved_details.append({
                "detection_id": detection.detection_id,
                "entity_id": entity.entity_id,
                "tracking_id": entity.tracking_id,
                "entity_type": entity.entity_type,
                "frame_number": detection.frame_number,
                "timestamp": detection.timestamp,
                "bbox_x": detection.bbox_x,
                "bbox_y": detection.bbox_y,
                "bbox_width": detection.bbox_width,
                "bbox_height": detection.bbox_height,
                "confidence": detection.confidence,
            })

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during detection ingestion: {str(exc)}",
        )

    return {
        "entities_created": entities_created,
        "entities_reused": entities_reused,
        "detections_saved": len(saved_details),
        "saved_detection_details": saved_details,
    }

