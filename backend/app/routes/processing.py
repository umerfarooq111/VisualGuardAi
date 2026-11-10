"""
Processing Management Routes for VisualGuard AI
=================================================

Provides API endpoints for managing video processing tasks.

Endpoints:
  POST /api/processing/tasks       - Create a new processing task
  GET  /api/processing/tasks       - List all tasks (paginated)
  GET  /api/processing/tasks/{id}  - Get a specific task by ID
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.processing_task import (
    ProcessingTaskCreate,
    ProcessingTaskListResponse,
    ProcessingTaskResponse,
)
from app.services.processing_service import (
    create_processing_task,
    get_task_by_id,
    get_tasks_list,
)

router = APIRouter(prefix="/api/processing", tags=["Processing"])


@router.post(
    "/tasks",
    response_model=ProcessingTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a processing task",
    description=(
        "Create a new video processing task for a given media record. "
        "The task starts with status='pending' and progress=0."
    ),
)
def create_task_endpoint(
    payload: ProcessingTaskCreate,
    db: Session = Depends(get_db),
) -> ProcessingTaskResponse:
    """
    Create a new ProcessingTask.

    - **media_id**: ID of the media record to process (must exist).
    - **protection_type**: One of `faces`, `number_plates`, or `both`.
    - **blur_intensity**: Optional blur strength between 0 and 100.
    """
    task = create_processing_task(
        db=db,
        media_id=payload.media_id,
        protection_type=payload.protection_type,
        blur_intensity=payload.blur_intensity,
    )
    return ProcessingTaskResponse.model_validate(task)


@router.get(
    "/tasks",
    response_model=ProcessingTaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all processing tasks",
    description="Retrieve a paginated list of processing tasks ordered by newest first.",
)
def list_tasks_endpoint(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return"),
    db: Session = Depends(get_db),
) -> ProcessingTaskListResponse:
    """
    Return a paginated list of all processing tasks, newest first.
    """
    items, total = get_tasks_list(db=db, skip=skip, limit=limit)
    return ProcessingTaskListResponse(
        total=total,
        items=[ProcessingTaskResponse.model_validate(t) for t in items],
    )


@router.get(
    "/tasks/{task_id}",
    response_model=ProcessingTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a processing task by ID",
    description="Retrieve a specific processing task by its task_id.",
)
def get_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
) -> ProcessingTaskResponse:
    """
    Return details for a single processing task.

    - Returns HTTP 404 if no task with the given ID exists.
    """
    task = get_task_by_id(db=db, task_id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing task with id={task_id} not found.",
        )
    return ProcessingTaskResponse.model_validate(task)

