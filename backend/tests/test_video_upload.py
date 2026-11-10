"""
Unit and integration tests for the video upload API (POST /api/videos/upload).
Integrated with the official FYP Media table schema.
"""

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.config import BASE_DIR, settings
from app.database import ensure_default_user
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_db():
    """Ensure default user exists before running tests."""
    ensure_default_user()


def generate_synthetic_mp4(width: int = 64, height: int = 64, fps: int = 10, frames: int = 5) -> bytes:
    """
    Generate a minimal valid MP4 video in-memory using OpenCV.
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
        for i in range(frames):
            frame = np.full((height, width, 3), fill_value=(i * 40 % 255), dtype=np.uint8)
            writer.write(frame)
        writer.release()

        with open(temp_path, "rb") as f:
            video_bytes = f.read()
        return video_bytes
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_successful_video_upload():
    """
    Test 1: Verify successful video upload.
    - Status code 201 Created.
    - Proper metadata extraction (fps, duration_seconds, resolution).
    - File exists on local filesystem in backend/uploads/.
    - PostgreSQL 'Media' table has recorded the metadata.
    """
    video_bytes = generate_synthetic_mp4(width=120, height=80, fps=10, frames=10)
    files = {"file": ("sample_test_flight.mp4", io.BytesIO(video_bytes), "video/mp4")}

    response = client.post("/api/videos/upload", files=files)
    assert response.status_code == 201, response.text
    data = response.json()

    assert "media_id" in data
    assert data["user_id"] == 1
    assert data["file_name"] == "sample_test_flight.mp4"
    assert data["status"] == "uploaded"
    assert "metadata" in data
    assert data["metadata"]["width"] == 120
    assert data["metadata"]["height"] == 80
    assert data["metadata"]["fps"] == 10.0
    assert data["metadata"]["duration_seconds"] == 1.0
    assert data["metadata"]["file_size"] == len(video_bytes)

    # Verify physical file existence in backend/uploads/
    stored_path = (BASE_DIR / data["file_path"]).resolve()
    assert stored_path.exists(), f"Expected uploaded video file at {stored_path}"

    # Clean up via DELETE endpoint
    del_resp = client.delete(f"/api/videos/{data['media_id']}")
    assert del_resp.status_code == 204
    assert not stored_path.exists(), "File should be removed from disk upon record deletion"


def test_unsupported_file_format():
    """
    Test 2: Verify that unsupported file types (e.g. .txt, .pdf, .exe) are rejected.
    - Status code 400 Bad Request.
    - Helpful error message with allowed formats.
    - No orphaned file left in uploads directory.
    """
    uploads_before = set(settings.UPLOAD_DIR.glob("*"))

    dummy_content = b"This is a text document, not a video."
    files = {"file": ("malicious_script.txt", io.BytesIO(dummy_content), "text/plain")}

    response = client.post("/api/videos/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

    uploads_after = set(settings.UPLOAD_DIR.glob("*"))
    assert uploads_after == uploads_before, "No file should be written to uploads on rejection"


def test_oversized_file():
    """
    Test 3: Verify that files exceeding the maximum upload size limit are rejected.
    - Status code 413 Payload Too Large.
    - Partially written file is deleted immediately.
    """
    uploads_before = set(settings.UPLOAD_DIR.glob("*"))

    video_bytes = generate_synthetic_mp4(width=64, height=64, fps=5, frames=5)

    with patch.object(settings, "MAX_UPLOAD_SIZE_MB", 0.0005):
        with patch.object(settings.__class__, "max_upload_size_bytes", 1024):
            files = {"file": ("huge_video.mp4", io.BytesIO(video_bytes), "video/mp4")}
            response = client.post("/api/videos/upload", files=files)

    assert response.status_code == 413
    assert "File size exceeds maximum allowed limit" in response.json()["detail"]

    uploads_after = set(settings.UPLOAD_DIR.glob("*"))
    assert uploads_after == uploads_before, "Partially streamed file should be deleted on size limit violation"


def test_invalid_or_corrupted_video():
    """
    Test 4: Verify that corrupted or unreadable video files are caught by OpenCV.
    - Status code 400 Bad Request.
    - Clear diagnostic error message.
    - Uploaded corrupted file is deleted.
    """
    uploads_before = set(settings.UPLOAD_DIR.glob("*"))

    corrupt_bytes = b"CORRUPTED_HEADER_DATA_NOT_A_REAL_CONTAINER_STREAM_1234567890"
    files = {"file": ("corrupt_sample.mp4", io.BytesIO(corrupt_bytes), "video/mp4")}

    response = client.post("/api/videos/upload", files=files)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "corrupted" in detail.lower() or "cannot be decoded" in detail.lower() or "invalid" in detail.lower()

    uploads_after = set(settings.UPLOAD_DIR.glob("*"))
    assert uploads_after == uploads_before, "Corrupted file must be removed from disk"


def test_database_failure_and_local_cleanup():
    """
    Test 5: Verify that if database saving fails, the newly uploaded local file is deleted.
    - Status code 500 Internal Server Error.
    - File deleted from disk (no orphaned files).
    """
    uploads_before = set(settings.UPLOAD_DIR.glob("*"))
    video_bytes = generate_synthetic_mp4(width=64, height=64, fps=5, frames=5)
    files = {"file": ("db_fail_test.mp4", io.BytesIO(video_bytes), "video/mp4")}

    with patch("sqlalchemy.orm.Session.commit", side_effect=OperationalError("connection lost", {}, Exception())):
        response = client.post("/api/videos/upload", files=files)

    assert response.status_code == 500
    assert "Database error" in response.json()["detail"]

    uploads_after = set(settings.UPLOAD_DIR.glob("*"))
    assert uploads_after == uploads_before, "Uploaded file must be deleted if DB insert fails"
