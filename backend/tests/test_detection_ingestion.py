"""
Integration tests for POST /api/processing/tasks/{task_id}/detections.

Covers:
  - Successful ingestion (single entity, single detection)
  - Multiple entities and multiple detections in one request
  - Entity de-duplication (reuse existing entity row)
  - Invalid task ID → HTTP 404
  - Invalid entity_type → HTTP 422
  - Invalid frame_number (negative) → HTTP 422
  - Invalid bbox_width (zero / negative) → HTTP 422
  - confidence stored as NULL
  - Transaction rollback on DB failure
  - All existing tests still pass
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
from app.models.detected_entity import DetectedEntity
from app.models.detection import Detection

client = TestClient(app)

INGEST_URL = "/api/processing/tasks/{task_id}/detections"


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
    """Upload a real video and return its media_id."""
    video_bytes = _generate_mp4()
    files = {"file": ("ingest_test.mp4", io.BytesIO(video_bytes), "video/mp4")}
    resp = client.post("/api/videos/upload", files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()["media_id"]


@pytest.fixture()
def task_id(media_id: int) -> int:
    """Create a processing task for the uploaded video and return its task_id."""
    resp = client.post(
        "/api/processing/tasks",
        json={"media_id": media_id, "protection_type": "faces"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["task_id"]


def _make_detection(
    tracking_id="1",
    entity_type="face",
    frame_number=10,
    timestamp=0.5,
    bbox_x=5.0,
    bbox_y=5.0,
    bbox_width=50.0,
    bbox_height=60.0,
) -> dict:
    """Return a valid detection dict."""
    return dict(
        tracking_id=tracking_id,
        entity_type=entity_type,
        frame_number=frame_number,
        timestamp=timestamp,
        bbox_x=bbox_x,
        bbox_y=bbox_y,
        bbox_width=bbox_width,
        bbox_height=bbox_height,
    )


# ---------------------------------------------------------------------------
# Tests: successful ingestion
# ---------------------------------------------------------------------------


def test_ingest_single_detection_success(task_id: int, media_id: int):
    """
    Test 1: Ingest one detection event.
    Expect HTTP 201, correct counts, correct fields, confidence=NULL.
    """
    payload = {"detections": [_make_detection()]}
    resp = client.post(INGEST_URL.format(task_id=task_id), json=payload)
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["task_id"] == task_id
    assert data["media_id"] == media_id
    assert data["entities_created"] == 1
    assert data["entities_reused"] == 0
    assert data["detections_saved"] == 1

    det = data["detections"][0]
    assert det["tracking_id"] == "1"
    assert det["entity_type"] == "face"
    assert det["frame_number"] == 10
    assert det["timestamp"] == pytest.approx(0.5)
    assert det["bbox_x"] == pytest.approx(5.0)
    assert det["bbox_width"] == pytest.approx(50.0)
    assert det["confidence"] is None   # pipeline does not supply confidence


def test_ingest_multiple_entities_and_detections(task_id: int, media_id: int):
    """
    Test 2: Ingest 3 detections across 2 distinct entities.
    Expect 2 new entities and 3 saved detections.
    """
    detections = [
        _make_detection(tracking_id="A", entity_type="face", frame_number=1, timestamp=0.1),
        _make_detection(tracking_id="A", entity_type="face", frame_number=2, timestamp=0.2),
        _make_detection(tracking_id="B", entity_type="number_plate", frame_number=1, timestamp=0.1,
                        bbox_x=200.0, bbox_y=300.0, bbox_width=120.0, bbox_height=40.0),
    ]
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": detections})
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["entities_created"] == 2
    assert data["entities_reused"] == 0
    assert data["detections_saved"] == 3

    # All confidence values must be None
    for det in data["detections"]:
        assert det["confidence"] is None


def test_ingest_entity_deduplication(task_id: int, media_id: int):
    """
    Test 3: Send the same tracking_id/entity_type in two separate requests.
    Second request must reuse the existing entity (entities_reused=1, entities_created=0).
    """
    payload = {"detections": [_make_detection(tracking_id="DUP", entity_type="face", frame_number=5)]}

    # First request — creates the entity
    r1 = client.post(INGEST_URL.format(task_id=task_id), json=payload)
    assert r1.status_code == 201
    assert r1.json()["entities_created"] == 1
    entity_id_first = r1.json()["detections"][0]["entity_id"]

    # Second request — must reuse
    payload2 = {"detections": [_make_detection(tracking_id="DUP", entity_type="face", frame_number=6)]}
    r2 = client.post(INGEST_URL.format(task_id=task_id), json=payload2)
    assert r2.status_code == 201
    assert r2.json()["entities_created"] == 0
    assert r2.json()["entities_reused"] == 1
    assert r2.json()["detections"][0]["entity_id"] == entity_id_first


def test_ingest_same_tracking_different_type_creates_new(task_id: int):
    """
    Test 4: Same tracking_id but different entity_type must create a separate entity.
    """
    det1 = _make_detection(tracking_id="X", entity_type="face", frame_number=1)
    det2 = _make_detection(tracking_id="X", entity_type="number_plate", frame_number=2,
                           bbox_x=0.0, bbox_y=0.0, bbox_width=10.0, bbox_height=5.0)
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [det1, det2]})
    assert resp.status_code == 201
    data = resp.json()
    assert data["entities_created"] == 2
    assert data["detections_saved"] == 2
    ids = {d["entity_id"] for d in data["detections"]}
    assert len(ids) == 2  # two distinct entity rows


def test_ingest_number_plate_entity_type(task_id: int):
    """
    Test 5: 'number_plate' is a valid entity_type.
    """
    payload = {"detections": [
        _make_detection(tracking_id="99", entity_type="number_plate",
                        bbox_x=0.0, bbox_y=0.0, bbox_width=80.0, bbox_height=25.0)
    ]}
    resp = client.post(INGEST_URL.format(task_id=task_id), json=payload)
    assert resp.status_code == 201
    assert resp.json()["detections"][0]["entity_type"] == "number_plate"


# ---------------------------------------------------------------------------
# Tests: confidence is always NULL
# ---------------------------------------------------------------------------


def test_confidence_is_null_in_database(task_id: int):
    """
    Test 6: Verify that the saved Detection row in the DB has confidence=NULL.
    """
    payload = {"detections": [_make_detection(tracking_id="CONF", frame_number=77)]}
    resp = client.post(INGEST_URL.format(task_id=task_id), json=payload)
    assert resp.status_code == 201
    detection_id = resp.json()["detections"][0]["detection_id"]

    db = SessionLocal()
    try:
        row = db.query(Detection).filter(Detection.detection_id == detection_id).first()
        assert row is not None
        assert row.confidence is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests: 404 — invalid task ID
# ---------------------------------------------------------------------------


def test_ingest_invalid_task_id():
    """
    Test 7: POST to a non-existent task_id → HTTP 404.
    """
    payload = {"detections": [_make_detection()]}
    resp = client.post(INGEST_URL.format(task_id=999_999), json=payload)
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: 422 — validation errors
# ---------------------------------------------------------------------------


def test_ingest_invalid_entity_type(task_id: int):
    """
    Test 8: Unsupported entity_type → HTTP 422.
    """
    bad = _make_detection(entity_type="vehicle")
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [bad]})
    assert resp.status_code == 422, resp.text


def test_ingest_negative_frame_number(task_id: int):
    """
    Test 9: Negative frame_number → HTTP 422.
    """
    bad = _make_detection(frame_number=-1)
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [bad]})
    assert resp.status_code == 422, resp.text


def test_ingest_negative_timestamp(task_id: int):
    """
    Test 10: Negative timestamp → HTTP 422.
    """
    bad = _make_detection(timestamp=-0.1)
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [bad]})
    assert resp.status_code == 422, resp.text


def test_ingest_zero_bbox_width(task_id: int):
    """
    Test 11: bbox_width=0 → HTTP 422 (must be > 0).
    """
    bad = _make_detection(bbox_width=0.0)
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [bad]})
    assert resp.status_code == 422, resp.text


def test_ingest_zero_bbox_height(task_id: int):
    """
    Test 12: bbox_height=0 → HTTP 422 (must be > 0).
    """
    bad = _make_detection(bbox_height=0.0)
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [bad]})
    assert resp.status_code == 422, resp.text


def test_ingest_negative_bbox_x(task_id: int):
    """
    Test 13: bbox_x < 0 → HTTP 422.
    """
    bad = _make_detection(bbox_x=-1.0)
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [bad]})
    assert resp.status_code == 422, resp.text


def test_ingest_empty_detections_list(task_id: int):
    """
    Test 14: Empty detections list → HTTP 422 (min_length=1).
    """
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": []})
    assert resp.status_code == 422, resp.text


def test_ingest_missing_tracking_id(task_id: int):
    """
    Test 15: Missing tracking_id → HTTP 422.
    """
    bad = _make_detection()
    del bad["tracking_id"]
    resp = client.post(INGEST_URL.format(task_id=task_id), json={"detections": [bad]})
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Tests: transaction rollback on DB failure
# ---------------------------------------------------------------------------


def test_ingest_transaction_rollback_on_db_error(task_id: int, media_id: int):
    """
    Test 16: If a SQLAlchemyError is raised during ingestion, the transaction must
    be rolled back (no partial DetectedEntity or Detection rows left).
    """
    db = SessionLocal()
    entity_count_before = db.query(DetectedEntity).filter(
        DetectedEntity.media_id == media_id
    ).count()
    detection_count_before = db.query(Detection).count()
    db.close()

    # Patch db.flush() to raise a SQLAlchemyError on the first call
    original_flush = None

    def exploding_flush(*args, **kwargs):
        raise SQLAlchemyError("Simulated DB failure during flush")

    with patch(
        "app.services.processing_service.DetectedEntity",
        side_effect=SQLAlchemyError("Simulated DB failure"),
    ):
        payload = {"detections": [_make_detection(tracking_id="FAIL_ENTITY")]}
        resp = client.post(INGEST_URL.format(task_id=task_id), json=payload)

    assert resp.status_code == 500, resp.text
    assert "database error" in resp.json()["detail"].lower()

    # Verify no new rows were left in DB
    db = SessionLocal()
    entity_count_after = db.query(DetectedEntity).filter(
        DetectedEntity.media_id == media_id
    ).count()
    detection_count_after = db.query(Detection).count()
    db.close()

    assert entity_count_after == entity_count_before
    assert detection_count_after == detection_count_before

