"""
Processed Outputs Service Layer for VisualGuard AI
===================================================

Handles:
- Receiving and storing processed video files from the AI pipeline.
- Registering metadata in the PROCESSED_MEDIA PostgreSQL table.
- Listing and retrieving processed output records.
- Streaming and downloading processed video files.
- Safe deletion of processed outputs (file + DB record).

Storage location: backend/outputs/

Security:
- Path-traversal is prevented by resolving every file path against
  settings.OUTPUT_DIR and verifying it is a child of that directory.
- Only MP4 files are accepted for save operations.
"""

import re
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.models.media import Media
from app.models.processed_media import ProcessedMedia
from app.models.processing_task import ProcessingTask

# Only MP4 is accepted — consistent with the H.264/yuv420p/faststart requirement
ALLOWED_OUTPUT_EXTENSIONS = {".mp4"}
CHUNK_SIZE = 1 * 1024 * 1024  # 1 MB streaming chunks


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sanitize_stem(name: str) -> str:
    """Remove unsafe characters from a filename stem."""
    clean = re.sub(r"[^\w\.-]", "_", name)
    return clean.strip("._") or "output"


def _resolve_output_path(relative_or_stored: str) -> Path:
    """
    Resolve a stored relative path (e.g. 'outputs/abc.mp4') to an absolute Path
    under OUTPUT_DIR.  Raises HTTPException 400 on path-traversal attempts.
    """
    # Stored paths look like "outputs/<filename>"
    stem = Path(relative_or_stored).name  # just the filename
    resolved = (settings.OUTPUT_DIR / stem).resolve()

    # Path-traversal guard: resolved must be inside OUTPUT_DIR
    try:
        resolved.relative_to(settings.OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path: path traversal is not allowed.",
        )
    return resolved


def _get_task_or_404(db: Session, task_id: int) -> ProcessingTask:
    """Retrieve a ProcessingTask by PK or raise HTTP 404."""
    task = db.query(ProcessingTask).filter(ProcessingTask.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing task with id={task_id} not found.",
        )
    return task


def _get_media_or_404(db: Session, media_id: int) -> Media:
    """Retrieve a Media record by PK or raise HTTP 404."""
    media = db.query(Media).filter(Media.media_id == media_id).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media with id={media_id} not found.",
        )
    return media


def _get_processed_or_404(db: Session, processed_id: int) -> ProcessedMedia:
    """Retrieve a ProcessedMedia record by PK or raise HTTP 404."""
    record = (
        db.query(ProcessedMedia)
        .filter(ProcessedMedia.processed_id == processed_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processed output with id={processed_id} not found.",
        )
    return record


# ---------------------------------------------------------------------------
# Save processed output
# ---------------------------------------------------------------------------


def save_processed_output(
    db: Session,
    upload_file: UploadFile,
    task_id: int,
    output_type: str,
) -> dict:
    """
    Persist a processed video file to backend/outputs/ and register its
    metadata in the PROCESSED_MEDIA table.

    Steps:
    1. Validate task exists, derive media_id.
    2. Validate file extension (.mp4 only).
    3. Stream file to a unique path under OUTPUT_DIR.
    4. Insert a ProcessedMedia row.
    5. On DB failure, delete the file (orphan cleanup).
    6. Mark the processing task as 'completed' (only after successful save).

    Returns:
        dict with processed_id, media_id, task_id, filename, output_path,
              output_type, file_size.

    Raises:
        HTTPException (404): task not found.
        HTTPException (400): unsupported file extension.
        HTTPException (500): filesystem or DB error.
    """
    task = _get_task_or_404(db, task_id)
    media_id = task.media_id

    # Validate extension
    original_name = upload_file.filename or "output.mp4"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_OUTPUT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_OUTPUT_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported output format '{ext or 'unknown'}'. Allowed: {allowed}",
        )

    stem = _sanitize_stem(Path(original_name).stem)
    unique_id = uuid.uuid4().hex[:12]
    stored_filename = f"{unique_id}_{stem}{ext}"
    dest_path = (settings.OUTPUT_DIR / stored_filename).resolve()

    # Path-traversal guard
    try:
        dest_path.relative_to(settings.OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal is not allowed.",
        )

    # Stream to disk
    total_bytes = 0
    try:
        with open(dest_path, "wb") as buf:
            while chunk := upload_file.file.read(CHUNK_SIZE):
                total_bytes += len(chunk)
                buf.write(chunk)
    except Exception as exc:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write processed output to disk: {exc}",
        )

    if total_bytes == 0:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded processed video file is empty.",
        )

    relative_path = f"outputs/{stored_filename}"

    # Persist metadata
    record = ProcessedMedia(
        media_id=media_id,
        output_path=relative_path,
        output_type=output_type,
    )
    try:
        db.add(record)
        db.flush()  # get processed_id before marking task complete

        # Mark task completed — only after the output row is safely staged
        task.status = "completed"
        db.commit()
        db.refresh(record)
    except SQLAlchemyError as exc:
        db.rollback()
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while saving processed output: {exc}",
        )

    return {
        "processed_id": record.processed_id,
        "media_id": media_id,
        "task_id": task_id,
        "filename": stored_filename,
        "output_path": relative_path,
        "output_type": output_type,
        "file_size": total_bytes,
    }


# ---------------------------------------------------------------------------
# List / retrieve
# ---------------------------------------------------------------------------


def list_outputs_for_media(
    db: Session,
    media_id: int,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[ProcessedMedia], int]:
    """
    Return paginated processed outputs for a given media_id.

    Raises:
        HTTPException (404): If the media record does not exist.
    """
    _get_media_or_404(db, media_id)
    query = db.query(ProcessedMedia).filter(ProcessedMedia.media_id == media_id)
    total = query.count()
    items = (
        query.order_by(ProcessedMedia.processed_id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_output_by_id(db: Session, processed_id: int) -> ProcessedMedia:
    """
    Return a single ProcessedMedia record or raise HTTP 404.
    """
    return _get_processed_or_404(db, processed_id)


# ---------------------------------------------------------------------------
# File access helpers (for streaming / download)
# ---------------------------------------------------------------------------


def resolve_output_file(record: ProcessedMedia) -> Path:
    """
    Resolve the stored relative path to an absolute Path and verify the
    file exists.

    Raises:
        HTTPException (404): file not found on disk.
        HTTPException (400): path traversal attempt.
    """
    abs_path = _resolve_output_path(record.output_path)
    if not abs_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processed output file not found on disk: {record.output_path}",
        )
    return abs_path


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def delete_output(db: Session, record: ProcessedMedia) -> None:
    """
    Delete a ProcessedMedia record and its physical file.

    - Attempts to remove the file first (non-fatal if already missing).
    - Deletes the DB record.
    - Rolls back and raises HTTP 500 on SQLAlchemyError.
    """
    # Remove file (best-effort; missing file is not an error)
    try:
        abs_path = _resolve_output_path(record.output_path)
        if abs_path.exists():
            abs_path.unlink()
    except HTTPException:
        pass  # path traversal on stored path — skip file removal, still delete record
    except OSError:
        pass  # file already gone — that's fine

    try:
        db.delete(record)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while deleting processed output: {exc}",
        )

