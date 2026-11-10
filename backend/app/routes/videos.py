"""
API routes for video media upload, retrieval, and management.
Integrated with the official FYP 'Media' database table.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.media import MediaListResponse, MediaResponse, MediaUploadResponse
from app.services.video_service import (
    delete_media_record,
    get_media_by_id,
    get_media_list,
    process_video_upload,
)

router = APIRouter(prefix="/api/videos", tags=["Videos"])


@router.post(
    "/upload",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video file",
    description="Upload an original video file to local storage (backend/uploads/). "
    "Validates format and size, extracts metadata via OpenCV, and persists to PostgreSQL 'Media' table.",
)
def upload_video(
    file: UploadFile = File(..., description="Video file to upload (.mp4, .avi, .mov, .mkv, .webm)"),
    user_id: int = Query(1, ge=1, description="ID of the user uploading this media"),
    db: Session = Depends(get_db),
) -> MediaUploadResponse:
    """
    Handle video upload, local file persistence, and metadata extraction.
    """
    return process_video_upload(upload_file=file, db=db, user_id=user_id)


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
    summary="Get media details by ID",
    description="Retrieve metadata for a previously uploaded media record.",
)
def get_video(
    media_id: int,
    db: Session = Depends(get_db),
) -> MediaResponse:
    """
    Retrieve media metadata by primary key ID.
    """
    media = get_media_by_id(db=db, media_id=media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media with ID {media_id} not found.",
        )
    return MediaResponse.model_validate(media)


@router.get(
    "",
    response_model=MediaListResponse,
    summary="List uploaded media",
    description="Retrieve a paginated list of all uploaded media records.",
)
def list_videos(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max number of records to return"),
    db: Session = Depends(get_db),
) -> MediaListResponse:
    """
    Retrieve list of uploaded media records.
    """
    items, total = get_media_list(db=db, skip=skip, limit=limit)
    response_items = [MediaResponse.model_validate(m) for m in items]
    return MediaListResponse(total=total, items=response_items)


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a media record",
    description="Delete a media record from the database and remove the physical file from disk.",
)
def delete_video(
    media_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a media record and its corresponding file.
    """
    media = get_media_by_id(db=db, media_id=media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media with ID {media_id} not found.",
        )
    delete_media_record(db=db, media=media)
