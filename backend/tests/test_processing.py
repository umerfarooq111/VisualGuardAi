"""
Integration tests for the Processing Management API.

Covers:
  - POST /api/processing/tasks
  - GET  /api/processing/tasks
  - GET  /api/processing/tasks/{task_id}
"""

import io
import os
import tempfile

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.database import ensure_default_user, SessionLocal
from app.main import app
from app.models.processing_task import ProcessingTask

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def init_db():
    """Ensure the default user (user_id=1) exists before every test."""
    ensure_default_user()


def _generate_mp4(width: int = 64, height: int = 64, fps: int = 10, frames: int = 5) -> bytes:
    """Generate a minimal valid MP4 video in-memory using OpenCV."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
        for i in range(frames):
            frame = np.full((height, width, 3), fill_value=(i * 40 % 255), dtype=np.uint8)
            writer.write(frame)
        writer.release()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.fixture()
def uploaded_media_id() -> int:
    """
    Upload a real video and return the media_id for use in processing tests.
    Cleans up the processing task rows created during the test, but leaves
    the media row (it has no effect on other tests).
    """
    video_bytes = _generate_mp4()
    files = {"file": ("proc_test_video.mp4", io.BytesIO(video_bytes), "video/mp4")}
    resp = client.post("/api/videos/upload", files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()["media_id"]


# ---------------------------------------------------------------------------
# Tests: POST /api/processing/tasks
# ---------------------------------------------------------------------------


def test_create_task_success_faces(uploaded_media_id: int):
    """
    Test 1: Create a task with protection_type='faces' and no blur_intensity.
    Expect HTTP 201 and correct initial values.
    """
    payload = {"media_id": uploaded_media_id, "protection_type": "faces"}
    resp = client.post("/api/processing/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["task_id"] > 0
    assert data["media_id"] == uploaded_media_id
    assert data["protection_type"] == "faces"
    assert data["status"] == "pending"
    assert data["progress"] == 0.0
    assert data["blur_intensity"] is None
    assert data["error_message"] is None
    assert "created_at" in data
    assert "updated_at" in data


def test_create_task_success_number_plates_with_blur(uploaded_media_id: int):
    """
    Test 2: Create a task with protection_type='number_plates' and blur_intensity=50.
    """
    payload = {
        "media_id": uploaded_media_id,
        "protection_type": "number_plates",
        "blur_intensity": 50.0,
    }
    resp = client.post("/api/processing/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["protection_type"] == "number_plates"
    assert data["blur_intensity"] == 50.0
    assert data["status"] == "pending"


def test_create_task_success_both(uploaded_media_id: int):
    """
    Test 3: Create a task with protection_type='both'.
    """
    payload = {
        "media_id": uploaded_media_id,
        "protection_type": "both",
        "blur_intensity": 0.0,
    }
    resp = client.post("/api/processing/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    assert resp.json()["protection_type"] == "both"
    assert resp.json()["blur_intensity"] == 0.0


def test_create_task_nonexistent_media():
    """
    Test 4: Create a task referencing a media_id that does not exist.
    Expect HTTP 404.
    """
    payload = {"media_id": 999_999, "protection_type": "faces"}
    resp = client.post("/api/processing/tasks", json=payload)
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_create_task_invalid_protection_type(uploaded_media_id: int):
    """
    Test 5: Create a task with an unsupported protection_type.
    Expect HTTP 422 (validation error).
    """
    payload = {
        "media_id": uploaded_media_id,
        "protection_type": "invisible_cloak",
    }
    resp = client.post("/api/processing/tasks", json=payload)
    assert resp.status_code == 422, resp.text


def test_create_task_blur_intensity_too_high(uploaded_media_id: int):
    """
    Test 6: Create a task with blur_intensity above the max (100).
    Expect HTTP 422 (validation error).
    """
    payload = {
        "media_id": uploaded_media_id,
        "protection_type": "faces",
        "blur_intensity": 101.0,
    }
    resp = client.post("/api/processing/tasks", json=payload)
    assert resp.status_code == 422, resp.text


def test_create_task_blur_intensity_negative(uploaded_media_id: int):
    """
    Test 7: Create a task with blur_intensity below 0.
    Expect HTTP 422 (validation error).
    """
    payload = {
        "media_id": uploaded_media_id,
        "protection_type": "faces",
        "blur_intensity": -1.0,
    }
    resp = client.post("/api/processing/tasks", json=payload)
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Tests: GET /api/processing/tasks
# ---------------------------------------------------------------------------


def test_list_tasks_returns_200(uploaded_media_id: int):
    """
    Test 8: GET /api/processing/tasks returns HTTP 200 with correct structure.
    """
    # Create at least one task so the list is non-empty
    client.post(
        "/api/processing/tasks",
        json={"media_id": uploaded_media_id, "protection_type": "faces"},
    )
    resp = client.get("/api/processing/tasks")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


def test_list_tasks_pagination(uploaded_media_id: int):
    """
    Test 9: Pagination parameters (skip, limit) work correctly.
    """
    # Create two tasks
    for _ in range(2):
        client.post(
            "/api/processing/tasks",
            json={"media_id": uploaded_media_id, "protection_type": "both"},
        )

    resp_full = client.get("/api/processing/tasks?skip=0&limit=200")
    total = resp_full.json()["total"]

    resp_limited = client.get("/api/processing/tasks?skip=0&limit=1")
    assert resp_limited.status_code == 200, resp_limited.text
    assert len(resp_limited.json()["items"]) == 1
    assert resp_limited.json()["total"] == total


# ---------------------------------------------------------------------------
# Tests: GET /api/processing/tasks/{task_id}
# ---------------------------------------------------------------------------


def test_get_task_by_id_success(uploaded_media_id: int):
    """
    Test 10: GET /api/processing/tasks/{task_id} returns correct task details.
    """
    create_resp = client.post(
        "/api/processing/tasks",
        json={
            "media_id": uploaded_media_id,
            "protection_type": "faces",
            "blur_intensity": 25.0,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    task_id = create_resp.json()["task_id"]

    get_resp = client.get(f"/api/processing/tasks/{task_id}")
    assert get_resp.status_code == 200, get_resp.text
    data = get_resp.json()

    assert data["task_id"] == task_id
    assert data["media_id"] == uploaded_media_id
    assert data["protection_type"] == "faces"
    assert data["blur_intensity"] == 25.0
    assert data["status"] == "pending"
    assert data["progress"] == 0.0


def test_get_task_by_id_not_found():
    """
    Test 11: GET /api/processing/tasks/{task_id} returns HTTP 404 for unknown ID.
    """
    resp = client.get("/api/processing/tasks/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()

