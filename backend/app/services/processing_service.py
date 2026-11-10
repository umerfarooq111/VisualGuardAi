"""
Processing Service Layer for VisualGuard AI
============================================

Handles:
- Creating processing task records in the PROCESSING_TASK table.
- Validating that the referenced media exists.
- Retrieving single tasks and paginated task lists.
"""

from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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

