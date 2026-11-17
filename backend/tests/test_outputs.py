"""
Integration tests for the Processed Outputs Management API.

Covers:
  POST   /api/outputs/save
  GET    /api/outputs/media/{media_id}
  GET    /api/outputs/{processed_id}
  GET    /api/outputs/{processed_id}/preview
  GET    /api/outputs/{processed_id}/download
  DELETE /api/outputs/{processed_id}
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
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import SessionLocal, ensure_default_user
from app.main import app
from app.models.processed_media import ProcessedMedia
from app.models.processing_task import ProcessingTask

client = TestClient(app)
SAVE_URL = "/api/outputs/save"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def init_db():
    """Ensure the default user (user_id=1) exists before every test."""
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
            frame = np.full((height, width, 3), fill_value=(i * 50 % 255), dtype=np.uint8)
            writer.write(frame)
        writer.release()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.fixture()
def media_id() -> int:
    """Upload a real video and return its media_id."""
    video_bytes = _generate_mp4()
    files = {"file": ("outputs_test.mp4", io.BytesIO(video_bytes), "video/mp4")}
    resp = client.post("/api/videos/upload", files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()["media_id"]


@pytest.fixture()
def task_id(media_id: int) -> int:
    """Create a processing task and return its task_id."""
    resp = client.post(
        "/api/processing/tasks",
        json={"media_id": media_id, "protection_type": "faces"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["task_id"]


@pytest.fixture()
def saved_output(task_id: int, media_id: int) -> dict:
    """
    Save one processed output and return the full response dict.
    Cleans up the output file and DB record after the test.
    """
    video_bytes = _generate_mp4()
    files = {"file": ("processed_out.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "faces_blurred"}
    resp = client.post(SAVE_URL, files=files, data=data)
    assert resp.status_code == 201, resp.text
    result = resp.json()

    yield result

    # Cleanup: delete physical file if it still exists
    output_path = settings.OUTPUT_DIR / Path(result["output_path"]).name
    if output_path.exists():
        output_path.unlink()

    # Remove DB record if still present
    db = SessionLocal()
    rec = db.query(ProcessedMedia).filter(
        ProcessedMedia.processed_id == result["processed_id"]
    ).first()
    if rec:
        db.delete(rec)
        db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Tests: POST /api/outputs/save
# ---------------------------------------------------------------------------


def test_save_output_success(task_id: int, media_id: int):
    """
    Test 1: Successful save of a processed MP4 output.
    Expect HTTP 201, correct response fields, file on disk, DB record created.
    """
    video_bytes = _generate_mp4()
    files = {"file": ("result.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "faces_blurred"}

    resp = client.post(SAVE_URL, files=files, data=data)
    assert resp.status_code == 201, resp.text

    out = resp.json()
    assert out["task_id"] == task_id
    assert out["media_id"] == media_id
    assert out["output_type"] == "faces_blurred"
    assert out["filename"].endswith(".mp4")
    assert out["output_path"].startswith("outputs/")
    assert out["file_size"] == len(video_bytes)
    assert out["status"] == "saved"
    assert out["processed_id"] > 0

    # Physical file must exist
    abs_path = settings.OUTPUT_DIR / out["filename"]
    assert abs_path.exists(), f"Expected output file at {abs_path}"

    # DB record must exist
    db = SessionLocal()
    rec = db.query(ProcessedMedia).filter(
        ProcessedMedia.processed_id == out["processed_id"]
    ).first()
    assert rec is not None
    assert rec.media_id == media_id
    assert rec.output_type == "faces_blurred"
    db.close()

    # Cleanup
    abs_path.unlink(missing_ok=True)
    db = SessionLocal()
    r = db.query(ProcessedMedia).filter(
        ProcessedMedia.processed_id == out["processed_id"]
    ).first()
    if r:
        db.delete(r)
        db.commit()
    db.close()


def test_save_output_marks_task_completed(task_id: int):
    """
    Test 2: After saving an output the associated task status becomes 'completed'.
    """
    video_bytes = _generate_mp4()
    files = {"file": ("done.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}

    resp = client.post(SAVE_URL, files=files, data=data)
    assert resp.status_code == 201, resp.text
    processed_id = resp.json()["processed_id"]
    filename = resp.json()["filename"]

    db = SessionLocal()
    task = db.query(ProcessingTask).filter(ProcessingTask.task_id == task_id).first()
    assert task.status == "completed"
    rec = db.query(ProcessedMedia).filter(
        ProcessedMedia.processed_id == processed_id
    ).first()
    if rec:
        db.delete(rec)
        db.commit()
    db.close()
    (settings.OUTPUT_DIR / filename).unlink(missing_ok=True)


def test_save_output_unique_filenames(task_id: int):
    """
    Test 3: Two uploads with the same original filename must produce different stored names.
    """
    video_bytes = _generate_mp4()

    ids = []
    filenames = []
    for _ in range(2):
        files = {"file": ("same_name.mp4", io.BytesIO(video_bytes), "video/mp4")}
        data = {"task_id": str(task_id), "output_type": "protected_video"}
        r = client.post(SAVE_URL, files=files, data=data)
        assert r.status_code == 201, r.text
        ids.append(r.json()["processed_id"])
        filenames.append(r.json()["filename"])

    assert filenames[0] != filenames[1], "Filenames must be unique"

    # Cleanup
    db = SessionLocal()
    for pid, fn in zip(ids, filenames):
        (settings.OUTPUT_DIR / fn).unlink(missing_ok=True)
        rec = db.query(ProcessedMedia).filter(ProcessedMedia.processed_id == pid).first()
        if rec:
            db.delete(rec)
    db.commit()
    db.close()


def test_save_output_invalid_task_id():
    """
    Test 4: Save with a non-existent task_id → HTTP 404.
    """
    video_bytes = _generate_mp4()
    files = {"file": ("x.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": "999999", "output_type": "protected_video"}
    resp = client.post(SAVE_URL, files=files, data=data)
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_save_output_invalid_file_type(task_id: int):
    """
    Test 5: Uploading a non-MP4 file → HTTP 400.
    """
    files = {"file": ("video.avi", io.BytesIO(b"fake avi data"), "video/x-msvideo")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    resp = client.post(SAVE_URL, files=files, data=data)
    assert resp.status_code == 400, resp.text
    assert "unsupported" in resp.json()["detail"].lower()


def test_save_output_empty_file(task_id: int):
    """
    Test 6: Uploading an empty file → HTTP 400.
    """
    files = {"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    resp = client.post(SAVE_URL, files=files, data=data)
    assert resp.status_code == 400, resp.text


def test_save_output_db_failure_cleans_up_file(task_id: int):
    """
    Test 7: If the DB flush raises SQLAlchemyError after the file has been
    written to disk, the service must delete the orphaned file and return HTTP 500.
    """
    video_bytes = _generate_mp4()
    files = {"file": ("fail.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}

    # Track any .mp4 written to OUTPUT_DIR during this call
    written_paths: list = []
    _real_open = open

    def _tracking_open(path, mode="r", *args, **kwargs):
        p = Path(str(path))
        if "wb" in str(mode) and settings.OUTPUT_DIR.resolve() in p.resolve().parents:
            written_paths.append(p.resolve())
        return _real_open(path, mode, *args, **kwargs)

    from sqlalchemy.orm import Session as _Session
    _real_flush = _Session.flush

    def _exploding_flush(self, *args, **kwargs):
        raise SQLAlchemyError("simulated DB failure at flush")

    with patch("builtins.open", side_effect=_tracking_open), \
         patch.object(_Session, "flush", _exploding_flush):
        resp = client.post(SAVE_URL, files=files, data=data)

    assert resp.status_code == 500, resp.text
    assert "database error" in resp.json()["detail"].lower()

    # Every file written to OUTPUT_DIR must have been cleaned up
    for p in written_paths:
        assert not p.exists(), f"Orphaned output file left on disk: {p}"


# ---------------------------------------------------------------------------
# Tests: GET /api/outputs/media/{media_id}
# ---------------------------------------------------------------------------


def test_list_outputs_for_media_empty(media_id: int):
    """
    Test 8: Listing outputs for a media with no saved outputs → 200, total=0.
    """
    resp = client.get(f"/api/outputs/media/{media_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_outputs_for_media_with_data(saved_output: dict, media_id: int):
    """
    Test 9: After saving one output, list returns it correctly.
    """
    resp = client.get(f"/api/outputs/media/{media_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["processed_id"] == saved_output["processed_id"]
    assert item["media_id"] == media_id
    assert item["output_type"] == saved_output["output_type"]


def test_list_outputs_for_nonexistent_media():
    """
    Test 10: Listing outputs for a non-existent media_id → HTTP 404.
    """
    resp = client.get("/api/outputs/media/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_list_outputs_pagination(task_id: int, media_id: int):
    """
    Test 11: Pagination parameters (skip, limit) work correctly.
    """
    video_bytes = _generate_mp4()
    ids = []
    filenames = []
    for _ in range(3):
        files = {"file": ("page_test.mp4", io.BytesIO(video_bytes), "video/mp4")}
        data = {"task_id": str(task_id), "output_type": "protected_video"}
        r = client.post(SAVE_URL, files=files, data=data)
        assert r.status_code == 201, r.text
        ids.append(r.json()["processed_id"])
        filenames.append(r.json()["filename"])

    try:
        resp_all = client.get(f"/api/outputs/media/{media_id}?limit=200")
        total = resp_all.json()["total"]
        assert total >= 3

        resp_one = client.get(f"/api/outputs/media/{media_id}?skip=0&limit=1")
        assert resp_one.status_code == 200
        assert len(resp_one.json()["items"]) == 1
        assert resp_one.json()["total"] == total
    finally:
        db = SessionLocal()
        for pid, fn in zip(ids, filenames):
            (settings.OUTPUT_DIR / fn).unlink(missing_ok=True)
            rec = db.query(ProcessedMedia).filter(ProcessedMedia.processed_id == pid).first()
            if rec:
                db.delete(rec)
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# Tests: GET /api/outputs/{processed_id}
# ---------------------------------------------------------------------------


def test_get_output_by_id_success(saved_output: dict):
    """
    Test 12: GET metadata for an existing output → HTTP 200, correct fields.
    """
    resp = client.get(f"/api/outputs/{saved_output['processed_id']}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["processed_id"] == saved_output["processed_id"]
    assert data["output_type"] == saved_output["output_type"]


def test_get_output_by_id_not_found():
    """
    Test 13: GET metadata for a non-existent processed_id → HTTP 404.
    """
    resp = client.get("/api/outputs/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: GET /api/outputs/{processed_id}/preview
# ---------------------------------------------------------------------------


def test_preview_output_success(saved_output: dict):
    """
    Test 14: Streaming preview returns 200, content-type video/mp4, non-empty body.
    """
    resp = client.get(f"/api/outputs/{saved_output['processed_id']}/preview")
    assert resp.status_code == 200, resp.text
    assert "video/mp4" in resp.headers.get("content-type", "")
    assert len(resp.content) > 0


def test_preview_output_not_found_in_db():
    """
    Test 15: Preview for a non-existent processed_id → HTTP 404.
    """
    resp = client.get("/api/outputs/999999/preview")
    assert resp.status_code == 404, resp.text


def test_preview_output_file_missing_on_disk(saved_output: dict):
    """
    Test 16: If the physical file is deleted after the DB record was saved,
    preview must return HTTP 404.
    """
    # Delete the physical file manually
    abs_path = settings.OUTPUT_DIR / Path(saved_output["output_path"]).name
    if abs_path.exists():
        abs_path.unlink()

    resp = client.get(f"/api/outputs/{saved_output['processed_id']}/preview")
    assert resp.status_code == 404, resp.text
    assert "not found on disk" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: GET /api/outputs/{processed_id}/download
# ---------------------------------------------------------------------------


def test_download_output_success(saved_output: dict):
    """
    Test 17: Download returns 200, content-type video/mp4, Content-Disposition attachment.
    """
    resp = client.get(f"/api/outputs/{saved_output['processed_id']}/download")
    assert resp.status_code == 200, resp.text
    assert "video/mp4" in resp.headers.get("content-type", "")
    disposition = resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert len(resp.content) > 0


def test_download_output_not_found_in_db():
    """
    Test 18: Download for a non-existent processed_id → HTTP 404.
    """
    resp = client.get("/api/outputs/999999/download")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Tests: DELETE /api/outputs/{processed_id}
# ---------------------------------------------------------------------------


def test_delete_output_success(task_id: int, media_id: int):
    """
    Test 19: Successful deletion removes the DB record and the physical file.
    """
    video_bytes = _generate_mp4()
    files = {"file": ("to_delete.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    save_resp = client.post(SAVE_URL, files=files, data=data)
    assert save_resp.status_code == 201, save_resp.text
    out = save_resp.json()
    processed_id = out["processed_id"]
    filename = out["filename"]
    abs_path = settings.OUTPUT_DIR / filename

    # Delete via API
    del_resp = client.delete(f"/api/outputs/{processed_id}")
    assert del_resp.status_code == 204, del_resp.text

    # File must be gone
    assert not abs_path.exists(), "Physical file should have been deleted"

    # DB record must be gone
    db = SessionLocal()
    rec = db.query(ProcessedMedia).filter(
        ProcessedMedia.processed_id == processed_id
    ).first()
    assert rec is None
    db.close()


def test_delete_output_not_found():
    """
    Test 20: Deleting a non-existent processed_id → HTTP 404.
    """
    resp = client.delete("/api/outputs/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_delete_output_missing_file_still_removes_db_record(task_id: int, media_id: int):
    """
    Test 21: If the physical file is already missing, delete must still remove
    the DB record (idempotent cleanup) and return 204.
    """
    video_bytes = _generate_mp4()
    files = {"file": ("ghost.mp4", io.BytesIO(video_bytes), "video/mp4")}
    data = {"task_id": str(task_id), "output_type": "protected_video"}
    save_resp = client.post(SAVE_URL, files=files, data=data)
    assert save_resp.status_code == 201, save_resp.text
    out = save_resp.json()
    processed_id = out["processed_id"]
    filename = out["filename"]

    # Manually remove the physical file first
    (settings.OUTPUT_DIR / filename).unlink(missing_ok=True)

    # API delete must still return 204
    del_resp = client.delete(f"/api/outputs/{processed_id}")
    assert del_resp.status_code == 204, del_resp.text

    # DB record must be gone
    db = SessionLocal()
    rec = db.query(ProcessedMedia).filter(
        ProcessedMedia.processed_id == processed_id
    ).first()
    assert rec is None
    db.close()
