"""
Processed Outputs Management Routes for VisualGuard AI
=======================================================

Provides API endpoints for managing processed video outputs.

Endpoints:
  POST   /api/outputs/save                      - Save a processed video from the AI pipeline
  GET    /api/outputs/media/{media_id}           - List outputs for a media record
  GET    /api/outputs/{processed_id}             - Get output metadata by ID
  GET    /api/outputs/{processed_id}/preview     - Stream the processed video for preview
  GET    /api/outputs/{processed_id}/download    - Download the processed video file
  DELETE /api/outputs/{processed_id}             - Delete output (file + DB record)
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.processed_media import (
    ProcessedMediaListResponse,
    ProcessedMediaResponse,
    ProcessedOutputSaveResponse,
)
from app.services.outputs_service import (
    delete_output,
    get_output_by_id,
    list_outputs_for_media,
    resolve_output_file,
    save_processed_output,
)

router = APIRouter(prefix="/api/outputs", tags=["Processed Outputs"])

# Streaming chunk size for video preview
_STREAM_CHUNK = 1 * 1024 * 1024  # 1 MB


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


@router.post(
    "/save",
    response_model=ProcessedOutputSaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a processed video output",
    description=(
        "Receive a processed video file from the AI pipeline, store it in "
        "backend/outputs/, register its metadata in PROCESSED_MEDIA, and mark "
        "the associated processing task as 'completed'. "
        "Only MP4 files are accepted. task_id is used to derive media_id."
    ),
)
def save_output_endpoint(
    file: UploadFile = File(..., description="Processed MP4 video file"),
    task_id: int = Form(..., gt=0, description="Processing task that produced this output"),
    output_type: str = Form(
        default="protected_video",
        description="Type of protection applied: protected_video | faces_blurred | plates_blurred | both_blurred",
    ),
    db: Session = Depends(get_db),
) -> ProcessedOutputSaveResponse:
    """
    Save a processed video output.

    - **file**: The MP4 video file produced by the AI pipeline.
    - **task_id**: The processing task that generated this output.
    - **output_type**: Description of the applied protection.

    The endpoint:
    1. Verifies the task exists and derives `media_id` from it.
    2. Validates the file is an MP4.
    3. Streams the file to `backend/outputs/` with a unique filename.
    4. Inserts a `PROCESSED_MEDIA` row.
    5. Marks the task `status='completed'`.
    """
    result = save_processed_output(
        db=db,
        upload_file=file,
        task_id=task_id,
        output_type=output_type,
    )
    return ProcessedOutputSaveResponse(**result)


# ---------------------------------------------------------------------------
# List outputs for a media record
# ---------------------------------------------------------------------------


@router.get(
    "/media/{media_id}",
    response_model=ProcessedMediaListResponse,
    status_code=status.HTTP_200_OK,
    summary="List processed outputs for a media record",
    description="Return all processed video outputs associated with the given media_id. Supports pagination.",
)
def list_outputs_endpoint(
    media_id: int,
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
) -> ProcessedMediaListResponse:
    """
    Return paginated processed outputs for a media record.

    - Returns HTTP 404 if the media record does not exist.
    - Returns an empty list if no outputs have been saved yet.
    """
    items, total = list_outputs_for_media(db=db, media_id=media_id, skip=skip, limit=limit)
    return ProcessedMediaListResponse(
        total=total,
        items=[ProcessedMediaResponse.model_validate(p) for p in items],
    )


# ---------------------------------------------------------------------------
# Retrieve metadata by ID
# ---------------------------------------------------------------------------


@router.get(
    "/{processed_id}",
    response_model=ProcessedMediaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get processed output metadata by ID",
    description="Retrieve metadata for a single processed output record.",
)
def get_output_endpoint(
    processed_id: int,
    db: Session = Depends(get_db),
) -> ProcessedMediaResponse:
    """
    Return metadata for a single processed output.

    - Returns HTTP 404 if the record does not exist.
    """
    record = get_output_by_id(db=db, processed_id=processed_id)
    return ProcessedMediaResponse.model_validate(record)


# ---------------------------------------------------------------------------
# Preview (streaming)
# ---------------------------------------------------------------------------


@router.get(
    "/{processed_id}/preview",
    status_code=status.HTTP_200_OK,
    summary="Stream processed video for browser preview",
    description=(
        "Stream the processed video file for in-browser preview. "
        "Returns the file as a chunked streaming response with MIME type video/mp4."
    ),
)
def preview_output_endpoint(
    processed_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Stream a processed video file for preview.

    - Returns HTTP 404 if the DB record or the physical file is missing.
    """
    record = get_output_by_id(db=db, processed_id=processed_id)
    abs_path = resolve_output_file(record)

    def _iter_file(path: Path, chunk: int):
        with open(path, "rb") as f:
            while data := f.read(chunk):
                yield data

    return StreamingResponse(
        _iter_file(abs_path, _STREAM_CHUNK),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'inline; filename="{abs_path.name}"',
            "Content-Length": str(abs_path.stat().st_size),
        },
    )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


@router.get(
    "/{processed_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download a processed video file",
    description=(
        "Download the processed video file as an attachment. "
        "Returns HTTP 404 if the record or the physical file is missing."
    ),
)
def download_output_endpoint(
    processed_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Trigger a file download for a processed output.

    - Returns HTTP 404 if the DB record or the physical file is missing.
    """
    record = get_output_by_id(db=db, processed_id=processed_id)
    abs_path = resolve_output_file(record)

    return FileResponse(
        path=str(abs_path),
        media_type="video/mp4",
        filename=abs_path.name,
        headers={"Content-Disposition": f'attachment; filename="{abs_path.name}"'},
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@router.delete(
    "/{processed_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a processed output",
    description=(
        "Delete a processed output record from the database and remove its "
        "physical file from disk. Missing files on disk are tolerated (idempotent cleanup)."
    ),
)
def delete_output_endpoint(
    processed_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a processed output and its file.

    - Returns HTTP 404 if the DB record does not exist.
    - A missing physical file is tolerated (the DB record is still deleted).
    """
    record = get_output_by_id(db=db, processed_id=processed_id)
    delete_output(db=db, record=record)

