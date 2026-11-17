"""
End-to-End API Workflow Integration Tests for VisualGuard AI.

Verifies the complete end-to-end flow matching the frontend user journey:
  1. Upload video (POST /api/videos/upload)
  2. Retrieve video details (GET /api/videos/{media_id})
  3. Create processing task (POST /api/processing/tasks)
  4. Start processing task (POST /api/processing/tasks/{task_id}/start)
  5. Update progress (PATCH /api/processing/tasks/{task_id}/progress)
  6. Ingest AI detection data (POST /api/processing/tasks/{task_id}/detections)
  7. Query detection results (GET /api/results/media/{media_id}/entities & detections)
  8. Save processed video output (POST /api/outputs/save)
  9. Verify task marked completed with progress 100% (GET /api/processing/tasks/{task_id})
  10. Stream preview of processed output (GET /api/outputs/{processed_id}/preview)
  11. Download processed output (GET /api/outputs/{processed_id}/download)
  12. Clean up output (DELETE /api/outputs/{processed_id})
  13. Clean up video (DELETE /api/videos/{media_id})
"""

import io
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import ensure_default_user
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_db():
    """Ensure the default user exists before running tests."""
    ensure_default_user()


def _generate_synthetic_mp4(width=64, height=64, fps=10, frames=5) -> bytes:
    """Generate a minimal valid MP4 video in memory using OpenCV."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
        for i in range(frames):
            frame = np.full((height, width, 3), fill_value=(i * 45 % 255), dtype=np.uint8)
            writer.write(frame)
        writer.release()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_complete_end_to_end_successful_lifecycle():
    """
    Execute the entire successful frontend journey end-to-end.
    """
    video_bytes = _generate_synthetic_mp4(width=128, height=128, fps=10, frames=10)

    # 1. Upload Video
    upload_files = {"file": ("e2e_car_drive.mp4", io.BytesIO(video_bytes), "video/mp4")}
    upload_resp = client.post("/api/videos/upload", files=upload_files)
    assert upload_resp.status_code == 201, upload_resp.text
    video_data = upload_resp.json()
    media_id = video_data["media_id"]
    assert media_id > 0
    assert video_data["status"] == "uploaded"
    assert video_data["metadata"]["width"] == 128
    assert video_data["metadata"]["height"] == 128

    # 2. Get Video Details & List
    get_video_resp = client.get(f"/api/videos/{media_id}")
    assert get_video_resp.status_code == 200
    assert get_video_resp.json()["file_name"] == "e2e_car_drive.mp4"

    list_videos_resp = client.get("/api/videos?skip=0&limit=50")
    assert list_videos_resp.status_code == 200
    assert any(v["media_id"] == media_id for v in list_videos_resp.json()["items"])

    # 3. Create Processing Task
    task_payload = {
        "media_id": media_id,
        "protection_type": "both",
        "blur_intensity": 45.0,
    }
    create_task_resp = client.post("/api/processing/tasks", json=task_payload)
    assert create_task_resp.status_code == 201, create_task_resp.text
    task_data = create_task_resp.json()
    task_id = task_data["task_id"]
    assert task_data["status"] == "pending"
    assert task_data["progress"] == 0.0
    assert task_data["protection_type"] == "both"

    # 4. Start Processing Task
    start_resp = client.post(f"/api/processing/tasks/{task_id}/start")
    assert start_resp.status_code == 200, start_resp.text
    assert start_resp.json()["status"] == "processing"

    # 5. Progress Updates
    p1 = client.patch(f"/api/processing/tasks/{task_id}/progress", json={"progress": 25.0})
    assert p1.status_code == 200
    assert p1.json()["progress"] == 25.0

    p2 = client.post(f"/api/processing/tasks/{task_id}/progress", json={"progress": 60.0})
    assert p2.status_code == 200
    assert p2.json()["progress"] == 60.0

    # 6. Ingest Detection Data
    detections_payload = {
        "detections": [
            {
                "tracking_id": "face_driver",
                "entity_type": "face",
                "frame_number": 2,
                "timestamp": 0.2,
                "bbox_x": 30.0,
                "bbox_y": 20.0,
                "bbox_width": 40.0,
                "bbox_height": 50.0,
            },
            {
                "tracking_id": "plate_front",
                "entity_type": "number_plate",
                "frame_number": 2,
                "timestamp": 0.2,
                "bbox_x": 50.0,
                "bbox_y": 80.0,
                "bbox_width": 60.0,
                "bbox_height": 20.0,
            },
        ]
    }
    ingest_resp = client.post(
        f"/api/processing/tasks/{task_id}/detections",
        json=detections_payload,
    )
    assert ingest_resp.status_code == 201, ingest_resp.text
    ingest_data = ingest_resp.json()
    assert ingest_data["entities_created"] == 2
    assert ingest_data["detections_saved"] == 2

    # Task status must still be 'processing'
    status_check = client.get(f"/api/processing/tasks/{task_id}")
    assert status_check.status_code == 200
    assert status_check.json()["status"] == "processing"

    # 7. Query Detection Results via Results APIs
    entities_resp = client.get(f"/api/results/media/{media_id}/entities")
    assert entities_resp.status_code == 200
    entities = entities_resp.json()["items"]
    assert len(entities) >= 2
    face_entity = next(e for e in entities if e["tracking_id"] == "face_driver")
    assert face_entity["entity_type"] == "face"

    dets_resp = client.get(f"/api/results/entities/{face_entity['entity_id']}/detections")
    assert dets_resp.status_code == 200
    assert len(dets_resp.json()["items"]) >= 1
    assert dets_resp.json()["items"][0]["frame_number"] == 2

    # 8. Save Processed Video Output
    processed_video_bytes = _generate_synthetic_mp4(width=128, height=128, fps=10, frames=10)
    output_files = {"file": ("e2e_car_drive_protected.mp4", io.BytesIO(processed_video_bytes), "video/mp4")}
    output_form = {"task_id": str(task_id), "output_type": "both_blurred"}

    save_resp = client.post("/api/outputs/save", files=output_files, data=output_form)
    assert save_resp.status_code == 201, save_resp.text
    save_data = save_resp.json()
    processed_id = save_data["processed_id"]
    assert processed_id > 0
    assert save_data["media_id"] == media_id
    assert save_data["task_id"] == task_id
    assert save_data["status"] == "saved"

    # 9. Verify Task Completion & Progress 100%
    completed_task = client.get(f"/api/processing/tasks/{task_id}").json()
    assert completed_task["status"] == "completed"
    assert completed_task["progress"] == 100.0

    # 10. Preview Processed Video (Streaming)
    preview_resp = client.get(f"/api/outputs/{processed_id}/preview")
    assert preview_resp.status_code == 200
    assert "video/mp4" in preview_resp.headers.get("content-type", "")
    assert len(preview_resp.content) > 0

    # 11. Download Processed Video
    download_resp = client.get(f"/api/outputs/{processed_id}/download")
    assert download_resp.status_code == 200
    assert "video/mp4" in download_resp.headers.get("content-type", "")
    assert "attachment" in download_resp.headers.get("content-disposition", "")
    assert len(download_resp.content) > 0

    # Verify listing outputs for media
    outputs_for_media = client.get(f"/api/outputs/media/{media_id}")
    assert outputs_for_media.status_code == 200
    assert any(o["processed_id"] == processed_id for o in outputs_for_media.json()["items"])

    # 12. Delete Processed Output
    del_out = client.delete(f"/api/outputs/{processed_id}")
    assert del_out.status_code == 204

    # Confirm 404 after deletion
    assert client.get(f"/api/outputs/{processed_id}").status_code == 404

    # 13. Delete Original Media
    del_media = client.delete(f"/api/videos/{media_id}")
    assert del_media.status_code == 204

    # Confirm 404 after deletion
    assert client.get(f"/api/videos/{media_id}").status_code == 404


def test_complete_end_to_end_failure_workflow():
    """
    Execute the lifecycle where a processing task encounters an error and fails:
    Upload -> Create Task -> Start -> Fail -> Verify cannot save output -> Clean up.
    """
    video_bytes = _generate_synthetic_mp4()
    upload_resp = client.post(
        "/api/videos/upload",
        files={"file": ("fail_workflow.mp4", io.BytesIO(video_bytes), "video/mp4")},
    )
    assert upload_resp.status_code == 201
    media_id = upload_resp.json()["media_id"]

    # Create task
    task_resp = client.post(
        "/api/processing/tasks",
        json={"media_id": media_id, "protection_type": "faces"},
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["task_id"]

    # Start task
    assert client.post(f"/api/processing/tasks/{task_id}/start").status_code == 200

    # Progress to 30%
    client.patch(f"/api/processing/tasks/{task_id}/progress", json={"progress": 30.0})

    # Fail task with error message
    fail_resp = client.post(
        f"/api/processing/tasks/{task_id}/fail",
        json={"error_message": "CUDA out of memory during face blur pipeline"},
    )
    assert fail_resp.status_code == 200
    assert fail_resp.json()["status"] == "failed"
    assert fail_resp.json()["error_message"] == "CUDA out of memory during face blur pipeline"

    # Verify task retrieval shows failed status and error message
    task_check = client.get(f"/api/processing/tasks/{task_id}").json()
    assert task_check["status"] == "failed"
    assert task_check["error_message"] == "CUDA out of memory during face blur pipeline"
    assert task_check["progress"] == 30.0

    # Output cannot be saved for a failed task
    save_attempt = client.post(
        "/api/outputs/save",
        files={"file": ("out.mp4", io.BytesIO(video_bytes), "video/mp4")},
        data={"task_id": str(task_id), "output_type": "faces_blurred"},
    )
    assert save_attempt.status_code == 400
    assert "failed" in save_attempt.json()["detail"].lower()

    # Clean up video
    assert client.delete(f"/api/videos/{media_id}").status_code == 204

