"""
Integration tests for Phase 6: Processing Task Lifecycle Management.

Covers:
  - Starting processing tasks (Pending -> Processing)
  - Prevent invalid start transitions (already processing, completed, failed)
  - Progress updates (0-100) via POST & PATCH
  - Rejecting invalid progress values (<0, >100)
  - Prevent progress updates on completed / failed tasks
  - Marking tasks as failed (error_message stored, status='failed')
  - Prevent failing already completed or failed tasks
  - Validating task retrieval reflects updated status, progress, error_message
  - Integration: detection ingestion does not alter task status
  - Integration: processed output storage marks task completed
  - Integration: processed output cannot be saved for a failed task
  - Database failure handling with rollback (500)
"""

import io
import os
import tempfile
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal, ensure_default_user
from app.main import app
from app.models.processing_task import ProcessingTask

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def init_db():
    """Ensure the default user exists before running tests."""
    ensure_default_user()


def _generate_mp4(width=64, height=64, fps=10, frames=5) -> bytes:
    """Generate a minimal valid MP4 video in memory using OpenCV."""
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
def media_id() -> int:
    """Upload a test video and return media_id."""
    video_bytes = _generate_mp4()
    files = {"file": ("lifecycle_test.mp4", io.BytesIO(video_bytes), "video/mp4")}
    resp = client.post("/api/videos/upload", files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()["media_id"]


@pytest.fixture()
def task_id(media_id: int) -> int:
    """Create a pending processing task and return task_id."""
    resp = client.post(
        "/api/processing/tasks",
        json={"media_id": media_id, "protection_type": "faces"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["task_id"]


# ---------------------------------------------------------------------------
# 1. Start Processing Tests
# ---------------------------------------------------------------------------


def test_start_processing_success(task_id: int):
    """
    Test 1: Start a pending processing task.
    Status transitions from 'pending' to 'processing'.
    """
    resp = client.post(f"/api/processing/tasks/{task_id}/start")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["task_id"] == task_id
    assert data["status"] == "processing"

    # Verify directly in DB
    db = SessionLocal()
    task = db.query(ProcessingTask).filter(ProcessingTask.task_id == task_id).first()
    assert task.status == "processing"
    db.close()


def test_start_processing_already_processing(task_id: int):
    """
    Test 2: Starting a task that is already processing must be rejected (400).
    """
    r1 = client.post(f"/api/processing/tasks/{task_id}/start")
    assert r1.status_code == 200

    r2 = client.post(f"/api/processing/tasks/{task_id}/start")
    assert r2.status_code == 400, r2.text
    assert "only 'pending' tasks can be started" in r2.json()["detail"].lower()


def test_start_processing_already_completed(task_id: int, media_id: int):
    """
    Test 3: Starting a task that is completed must be rejected (400).
    """
    video_bytes = _generate_mp4()
    files = {"file": ("complete.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    save_resp = client.post("/api/outputs/save", files=files, data=data)
    assert save_resp.status_code == 201

    resp = client.post(f"/api/processing/tasks/{task_id}/start")
    assert resp.status_code == 400, resp.text
    assert "cannot start task" in resp.json()["detail"].lower()


def test_start_processing_already_failed(task_id: int):
    """
    Test 4: Starting a task that has failed must be rejected (400).
    """
    fail_resp = client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "Model crash"},
    )
    assert fail_resp.status_code == 200

    resp = client.post(f"/api/processing/tasks/{task_id}/start")
    assert resp.status_code == 400, resp.text
    assert "cannot start task" in resp.json()["detail"].lower()


def test_start_processing_not_found():
    """
    Test 5: Starting a non-existent task returns 404.
    """
    resp = client.post("/api/processing/tasks/999999/start")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_start_processing_db_failure(task_id: int):
    """
    Test 6: DB failure during start rolls back and returns 500.
    """
    with patch("app.services.processing_service.Session.commit", side_effect=SQLAlchemyError("DB error")):
        resp = client.post(f"/api/processing/tasks/{task_id}/start")
    assert resp.status_code == 500, resp.text
    assert "database error" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. Progress Update Tests
# ---------------------------------------------------------------------------


def test_update_progress_success(task_id: int):
    """
    Test 7: Update progress percentage on an active task.
    Tests both POST and PATCH routes.
    """
    # Start task
    client.post(f"/api/processing/tasks/{task_id}/start")

    # PATCH progress to 35.5%
    resp1 = client.patch(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": 35.5},
    )
    assert resp1.status_code == 200, resp1.text
    assert resp1.json()["progress"] == 35.5

    # POST progress to 75.0%
    resp2 = client.post(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": 75.0},
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["progress"] == 75.0

    # Verify directly in DB
    db = SessionLocal()
    task = db.query(ProcessingTask).filter(ProcessingTask.task_id == task_id).first()
    assert task.progress == 75.0
    db.close()


def test_update_progress_boundary_values(task_id: int):
    """
    Test 8: 0.0 and 100.0 boundary values are accepted.
    """
    resp_zero = client.patch(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": 0.0},
    )
    assert resp_zero.status_code == 200
    assert resp_zero.json()["progress"] == 0.0

    resp_hundred = client.patch(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": 100.0},
    )
    assert resp_hundred.status_code == 200
    assert resp_hundred.json()["progress"] == 100.0


def test_update_progress_out_of_range_rejected(task_id: int):
    """
    Test 9: Values < 0.0 or > 100.0 are rejected with 422 Unprocessable Entity.
    """
    resp_neg = client.patch(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": -1.0},
    )
    assert resp_neg.status_code == 422, resp_neg.text

    resp_over = client.patch(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": 100.5},
    )
    assert resp_over.status_code == 422, resp_over.text


def test_update_progress_completed_task_rejected(task_id: int, media_id: int):
    """
    Test 10: Progress updates on a completed task must be rejected (400).
    """
    video_bytes = _generate_mp4()
    files = {"file": ("complete.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    client.post("/api/outputs/save", files=files, data=data)

    resp = client.patch(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": 50.0},
    )
    assert resp.status_code == 400, resp.text
    assert "cannot update progress" in resp.json()["detail"].lower()


def test_update_progress_failed_task_rejected(task_id: int):
    """
    Test 11: Progress updates on a failed task must be rejected (400).
    """
    client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "Pipeline crash"},
    )

    resp = client.patch(
        f"/api/processing/tasks/{task_id}/progress",
        json={"progress": 50.0},
    )
    assert resp.status_code == 400, resp.text
    assert "cannot update progress" in resp.json()["detail"].lower()


def test_update_progress_not_found():
    """
    Test 12: Progress update on non-existent task returns 404.
    """
    resp = client.patch(
        "/api/processing/tasks/999999/progress",
        json={"progress": 50.0},
    )
    assert resp.status_code == 404, resp.text


def test_update_progress_db_failure(task_id: int):
    """
    Test 13: DB failure during progress update returns 500.
    """
    with patch("app.services.processing_service.Session.commit", side_effect=SQLAlchemyError("DB error")):
        resp = client.patch(
            f"/api/processing/tasks/{task_id}/progress",
            json={"progress": 50.0},
        )
    assert resp.status_code == 500, resp.text


# ---------------------------------------------------------------------------
# 3. Failure Handling Tests
# ---------------------------------------------------------------------------


def test_fail_task_from_pending(task_id: int):
    """
    Test 14: Mark a pending task as failed.
    """
    resp = client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "Invalid video codec detected by pipeline"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "Invalid video codec detected by pipeline"

    # Verify directly in DB
    db = SessionLocal()
    task = db.query(ProcessingTask).filter(ProcessingTask.task_id == task_id).first()
    assert task.status == "failed"
    assert task.error_message == "Invalid video codec detected by pipeline"
    db.close()


def test_fail_task_from_processing(task_id: int):
    """
    Test 15: Mark a task that is currently processing as failed.
    """
    client.post(f"/api/processing/tasks/{task_id}/start")
    resp = client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "Out of memory during face detection"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "failed"
    assert resp.json()["error_message"] == "Out of memory during face detection"


def test_fail_task_already_completed_rejected(task_id: int, media_id: int):
    """
    Test 16: Failing a completed task must be rejected (400).
    """
    video_bytes = _generate_mp4()
    files = {"file": ("done.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    client.post("/api/outputs/save", files=files, data=data)

    resp = client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "Late failure"},
    )
    assert resp.status_code == 400, resp.text
    assert "already completed" in resp.json()["detail"].lower()


def test_fail_task_already_failed_rejected(task_id: int):
    """
    Test 17: Failing an already failed task must be rejected (400).
    """
    client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "First error"},
    )

    resp = client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "Second error"},
    )
    assert resp.status_code == 400, resp.text
    assert "already marked as failed" in resp.json()["detail"].lower()


def test_fail_task_empty_error_message(task_id: int):
    """
    Test 18: Empty error_message is rejected with 422.
    """
    resp = client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": ""},
    )
    assert resp.status_code == 422, resp.text


def test_fail_task_not_found():
    """
    Test 19: Failing non-existent task returns 404.
    """
    resp = client.post(
        "/api/processing/tasks/999999/fail",
        json={"error_message": "Error"},
    )
    assert resp.status_code == 404, resp.text


def test_fail_task_db_failure(task_id: int):
    """
    Test 20: DB failure during task fail returns 500.
    """
    with patch("app.services.processing_service.Session.commit", side_effect=SQLAlchemyError("DB error")):
        resp = client.post(
            f"/api/processing/tasks/{task_id}/fail",
            json={"error_message": "Error"},
        )
    assert resp.status_code == 500, resp.text


# ---------------------------------------------------------------------------
# 4. Task Status Retrieval Tests
# ---------------------------------------------------------------------------


def test_task_retrieval_shows_lifecycle_updates(task_id: int):
    """
    Test 21: GET /api/processing/tasks/{task_id} accurately reflects current
    status, progress, and error_message throughout the lifecycle.
    """
    # Initially pending, progress=0, error_message=None
    r_init = client.get(f"/api/processing/tasks/{task_id}")
    assert r_init.status_code == 200
    assert r_init.json()["status"] == "pending"
    assert r_init.json()["progress"] == 0.0
    assert r_init.json()["error_message"] is None

    # After start: status=processing
    client.post(f"/api/processing/tasks/{task_id}/start")
    r_start = client.get(f"/api/processing/tasks/{task_id}")
    assert r_start.json()["status"] == "processing"

    # After progress update: progress=60.0
    client.patch(f"/api/processing/tasks/{task_id}/progress", json={"progress": 60.0})
    r_prog = client.get(f"/api/processing/tasks/{task_id}")
    assert r_prog.json()["progress"] == 60.0

    # After fail: status=failed, error_message stored
    client.post(f"/api/processing/tasks/{task_id}/fail", json={"error_message": "Pipeline timeout"})
    r_fail = client.get(f"/api/processing/tasks/{task_id}")
    assert r_fail.json()["status"] == "failed"
    assert r_fail.json()["error_message"] == "Pipeline timeout"


# ---------------------------------------------------------------------------
# 5. Integration Verification Tests
# ---------------------------------------------------------------------------


def test_detection_ingestion_does_not_mark_task_completed(task_id: int):
    """
    Test 22: Ingesting detections must NOT mark a task as completed.
    Task status must remain as it was before ingestion.
    """
    # Start task
    client.post(f"/api/processing/tasks/{task_id}/start")

    # Ingest detection
    detection_payload = {
        "detections": [
            {
                "tracking_id": "face_1",
                "entity_type": "face",
                "frame_number": 1,
                "timestamp": 0.1,
                "bbox_x": 10.0,
                "bbox_y": 10.0,
                "bbox_width": 50.0,
                "bbox_height": 50.0,
            }
        ]
    }
    ingest_resp = client.post(
        f"/api/processing/tasks/{task_id}/detections",
        json=detection_payload,
    )
    assert ingest_resp.status_code == 201

    # Task status must still be 'processing', NOT 'completed'
    task_resp = client.get(f"/api/processing/tasks/{task_id}")
    assert task_resp.json()["status"] == "processing"


def test_output_storage_marks_task_completed_and_progress_100(task_id: int):
    """
    Test 23: Saving processed video output marks the task completed and progress=100.
    """
    client.post(f"/api/processing/tasks/{task_id}/start")
    client.patch(f"/api/processing/tasks/{task_id}/progress", json={"progress": 90.0})

    video_bytes = _generate_mp4()
    files = {"file": ("final.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    save_resp = client.post("/api/outputs/save", files=files, data=data)
    assert save_resp.status_code == 201

    # Task must now be completed with progress 100
    task_resp = client.get(f"/api/processing/tasks/{task_id}")
    assert task_resp.json()["status"] == "completed"
    assert task_resp.json()["progress"] == 100.0


def test_cannot_save_output_for_failed_task(task_id: int):
    """
    Test 24: Attempting to save processed output for a failed task is rejected (400).
    """
    client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "Fatal corruption in input video"},
    )

    video_bytes = _generate_mp4()
    files = {"file": ("fail_out.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    save_resp = client.post("/api/outputs/save", files=files, data=data)
    assert save_resp.status_code == 400, save_resp.text
    assert "failed" in save_resp.json()["detail"].lower()

