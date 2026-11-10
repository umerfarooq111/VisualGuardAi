"""
Video Service Layer for VisualGuard AI
======================================

Handles:
- Video file validation (formats, extensions, sizes).
- Local storage management (streaming upload to backend/uploads/).
- OpenCV metadata extraction (duration, fps, resolution).
- Verification of video integrity (detecting corrupt/unreadable files).
- Database persistence in PostgreSQL 'Media' table with automatic orphan cleanup upon failure.
"""

import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import cv2
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.config import BASE_DIR, settings
from app.database import ensure_default_user
from app.models.media import Media
from app.schemas.media import MediaMetadata, MediaUploadResponse

# Supported video container formats
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
CHUNK_SIZE = 1024 * 1024  # 1 MB chunk for streaming writes


def sanitize_filename(filename: str) -> str:
    """
    Remove potentially dangerous or invalid characters from a filename.
    """
    clean_name = re.sub(r"[^\w\.-]", "_", filename)
    return clean_name.strip("._") or "uploaded_video"


def validate_video_file_format(filename: str) -> str:
    """
    Validate that the uploaded file has an allowed video extension.

    Returns:
        str: Lowercase extension including the leading dot (e.g., '.mp4')

    Raises:
        HTTPException (400): If file format is not allowed.
    """
    ext = Path(filename).suffix.lower()
    if not ext or ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext or 'unknown'}'. Allowed video formats: {allowed}",
        )
    return ext


def save_uploaded_video_file(upload_file: UploadFile) -> Tuple[str, Path, int]:
    """
    Stream and persist an uploaded video file to the local uploads directory.
    Enforces maximum upload size constraints during streaming.

    Returns:
        Tuple[str, Path, int]: (stored_filename, destination_path, total_bytes)

    Raises:
        HTTPException (400): If file is empty or format is unsupported.
        HTTPException (413): If file exceeds MAX_UPLOAD_SIZE_MB.
        HTTPException (500): If filesystem write fails.
    """
    original_name = upload_file.filename or "video.mp4"
    ext = validate_video_file_format(original_name)
    clean_base = sanitize_filename(Path(original_name).stem)

    # Generate a collision-resistant unique filename
    unique_id = uuid.uuid4().hex[:12]
    stored_filename = f"{unique_id}_{clean_base}{ext}"
    destination_path = (settings.UPLOAD_DIR / stored_filename).resolve()

    max_bytes = settings.max_upload_size_bytes
    total_bytes = 0

    try:
        with open(destination_path, "wb") as buffer:
            while chunk := upload_file.file.read(CHUNK_SIZE):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    buffer.close()
                    if destination_path.exists():
                        destination_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded video file to disk: {str(exc)}",
        )

    if total_bytes == 0:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded video file is empty.",
        )

    return stored_filename, destination_path, total_bytes


def extract_and_verify_video_metadata(file_path: Path) -> Dict[str, Optional[Union[float, int]]]:
    """
    Extract technical properties (fps, resolution, duration) using OpenCV.
    Verifies that the video is valid and decodable.

    Returns:
        Dict: Metadata dictionary with 'duration', 'fps', 'width', 'height'.

    Raises:
        HTTPException (400): If the video cannot be opened or decoded.
    """
    metadata: Dict[str, Optional[Union[float, int]]] = {
        "duration": None,
        "fps": None,
        "width": None,
        "height": None,
    }

    cap = cv2.VideoCapture(str(file_path))
    try:
        if not cap.isOpened():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is corrupted, invalid, or cannot be decoded as a video.",
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        # Attempt to read the first frame to confirm decodability
        ret, _ = cap.read()
        if not ret or width <= 0 or height <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded video has no readable frames or invalid dimensions.",
            )

        metadata["width"] = width
        metadata["height"] = height
        if fps > 0:
            metadata["fps"] = round(fps, 2)
            if frame_count > 0:
                metadata["duration"] = round(float(frame_count / fps), 2)
    finally:
        cap.release()

    return metadata


def process_video_upload(
    upload_file: UploadFile,
    db: Session,
    user_id: int = 1,
) -> MediaUploadResponse:
    """
    Orchestrates the entire video upload pipeline:
    1. Ensures default user exists in the database.
    2. Validates format and streaming size.
    3. Persists file to backend/uploads/.
    4. Extracts and verifies video metadata using OpenCV.
    5. Persists metadata and local path to PostgreSQL 'Media' table.
    6. Cleans up orphaned file if database insertion fails.
    """
    ensure_default_user()
    original_filename = upload_file.filename or "video.mp4"

    # 1 & 2: Stream upload to local storage
    stored_filename, destination_path, file_size = save_uploaded_video_file(upload_file)

    # 3: Extract & verify metadata
    try:
        metadata = extract_and_verify_video_metadata(destination_path)
    except Exception:
        # If corrupted or unreadable, remove the uploaded file
        if destination_path.exists():
            destination_path.unlink()
        raise

    # 4: Save record to PostgreSQL 'Media' table
    relative_path = f"uploads/{stored_filename}"

    db_media = Media(
        user_id=user_id,
        file_name=original_filename,
        file_path=relative_path,
        duration_seconds=metadata.get("duration"),
        fps=metadata.get("fps"),
    )

    try:
        db.add(db_media)
        db.commit()
        db.refresh(db_media)
    except SQLAlchemyError as exc:
        db.rollback()
        # Clean up orphaned file on database error
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while recording media metadata: {str(exc)}",
        )

    # 5: Return structured response
    media_meta = MediaMetadata(
        duration_seconds=db_media.duration_seconds,
        fps=db_media.fps,
        width=metadata.get("width"),
        height=metadata.get("height"),
        file_size=file_size,
    )

    return MediaUploadResponse(
        media_id=db_media.media_id,
        user_id=db_media.user_id,
        file_name=db_media.file_name,
        file_path=db_media.file_path,
        status="uploaded",
        metadata=media_meta,
    )


def get_media_by_id(db: Session, media_id: int) -> Optional[Media]:
    """Retrieve a single media record by primary key ID."""
    return db.query(Media).filter(Media.media_id == media_id).first()


def get_media_list(db: Session, skip: int = 0, limit: int = 50) -> Tuple[List[Media], int]:
    """Retrieve a paginated list of media records along with total count."""
    query = db.query(Media)
    total = query.count()
    items = query.order_by(Media.media_id.desc()).offset(skip).limit(limit).all()
    return items, total


def delete_media_record(db: Session, media: Media) -> None:
    """
    Delete a media record from PostgreSQL and delete the local file from disk.
    """
    file_path = BASE_DIR / media.file_path if not Path(media.file_path).is_absolute() else Path(media.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    db.delete(media)
    db.commit()
