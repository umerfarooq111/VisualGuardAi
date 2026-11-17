"""
Processing Management Routes for VisualGuard AI
=================================================

Provides API endpoints for managing video processing tasks.

Endpoints:
  POST  /api/processing/tasks                          - Create a new processing task
  GET   /api/processing/tasks                          - List all tasks (paginated)
  GET   /api/processing/tasks/{task_id}                - Get a specific task by ID
  POST  /api/processing/tasks/{task_id}/start          - Start processing a pending task
  PATCH /api/processing/tasks/{task_id}/progress       - Update task progress (0-100)
  POST  /api/processing/tasks/{task_id}/fail           - Mark a task as failed
  POST  /api/processing/tasks/{task_id}/detections     - Ingest AI detection results
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.processing_task import (
    DetectionIngestionRequest,
    DetectionIngestionResponse,
    ProcessingTaskCreate,
    ProcessingTaskListResponse,
    ProcessingTaskResponse,
    SavedDetectionDetail,
    TaskFailRequest,
    TaskProgressUpdate,
)
from app.services.processing_service import (
    create_processing_task,
    fail_processing_task,
    get_task_by_id,
    get_tasks_list,
    ingest_detections,
    start_processing_task,
    update_task_progress,
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


# ---------------------------------------------------------------------------
# Task Lifecycle Management (Phase 6)
# ---------------------------------------------------------------------------


@router.post(
    "/tasks/{task_id}/start",
    response_model=ProcessingTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a processing task",
    description=(
        "Transition a processing task from 'pending' to 'processing'. "
        "Returns HTTP 400 if the task is already processing, completed, or failed."
    ),
)
def start_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
) -> ProcessingTaskResponse:
    """
    Start processing a task. Sets status='processing'.
    """
    task = start_processing_task(db=db, task_id=task_id)
    return ProcessingTaskResponse.model_validate(task)


@router.post(
    "/tasks/{task_id}/progress",
    response_model=ProcessingTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task progress (POST)",
    description="Update the progress percentage (0.0 to 100.0) of a processing task.",
)
@router.patch(
    "/tasks/{task_id}/progress",
    response_model=ProcessingTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task progress (PATCH)",
    description="Update the progress percentage (0.0 to 100.0) of a processing task.",
)
def update_progress_endpoint(
    task_id: int,
    payload: TaskProgressUpdate,
    db: Session = Depends(get_db),
) -> ProcessingTaskResponse:
    """
    Update progress percentage (0.0 - 100.0).
    """
    task = update_task_progress(db=db, task_id=task_id, progress=payload.progress)
    return ProcessingTaskResponse.model_validate(task)


@router.post(
    "/tasks/{task_id}/fail",
    response_model=ProcessingTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a processing task as failed",
    description=(
        "Transition a processing task to 'failed' and store an error message. "
        "Returns HTTP 400 if the task is already completed or failed."
    ),
)
def fail_task_endpoint(
    task_id: int,
    payload: TaskFailRequest,
    db: Session = Depends(get_db),
) -> ProcessingTaskResponse:
    """
    Mark a task as failed and record error_message.
    """
    task = fail_processing_task(db=db, task_id=task_id, error_message=payload.error_message)
    return ProcessingTaskResponse.model_validate(task)


@router.post(
    "/tasks/{task_id}/detections",
    response_model=DetectionIngestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest AI detection results for a processing task",
    description=(
        "Accept one or more detection events from the AI pipeline and persist them "
        "atomically into DETECTED_ENTITY and DETECTION tables. "
        "Entities are de-duplicated by (tracking_id, entity_type) for the task's media. "
        "confidence is always stored as NULL (not supplied by the pipeline)."
    ),
)
def ingest_detections_endpoint(
    task_id: int,
    payload: DetectionIngestionRequest,
    db: Session = Depends(get_db),
) -> DetectionIngestionResponse:
    """
    Ingest detection results produced by the AI pipeline for a processing task.

    - **task_id**: Must reference an existing ProcessingTask.
    - **detections**: List of detection events (entity + frame bounding box).

    Entity de-duplication:
    - Existing DetectedEntity rows with the same (tracking_id, entity_type) for
      the task's media_id are reused; new entities are created only when needed.

    Transaction safety:
    - All inserts happen in a single transaction. Any DB error triggers a full
      rollback so no partial records are written.
    """
    task = get_task_by_id(db=db, task_id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing task with id={task_id} not found.",
        )

    result = ingest_detections(
        db=db,
        task=task,
        detection_items=payload.detections,
    )

    return DetectionIngestionResponse(
        task_id=task_id,
        media_id=task.media_id,
        entities_created=result["entities_created"],
        entities_reused=result["entities_reused"],
        detections_saved=result["detections_saved"],
        detections=[
            SavedDetectionDetail(**d) for d in result["saved_detection_details"]
        ],
    )

