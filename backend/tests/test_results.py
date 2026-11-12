"""
Integration tests for the Detection & Results Management API.

Covers:
  GET /api/results/media/{media_id}/entities
  GET /api/results/entities/{entity_id}
  GET /api/results/entities/{entity_id}/detections
  GET /api/results/detections/{detection_id}
  GET /api/results/media/{media_id}/processed
  GET /api/results/processed/{processed_id}
  GET /api/results/processed/{processed_id}/selections
  GET /api/results/selections/{selection_id}

Test data is seeded directly through SQLAlchemy (no AI pipeline needed).
"""

import io
import os
import tempfile

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, ensure_default_user
from app.main import app
from app.models.detected_entity import DetectedEntity
from app.models.detection import Detection
from app.models.processed_media import ProcessedMedia
from app.models.selected_object import SelectedObject

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def init_db():
    """Ensure the default user (user_id=1) exists before every test."""
    ensure_default_user()


def _generate_mp4(width: int = 64, height: int = 64, fps: int = 10, frames: int = 5) -> bytes:
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
    files = {"file": ("results_test_video.mp4", io.BytesIO(video_bytes), "video/mp4")}
    resp = client.post("/api/videos/upload", files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()["media_id"]


@pytest.fixture()
def seeded_entity(media_id: int) -> DetectedEntity:
    """
    Seed a DetectedEntity row directly via SQLAlchemy and return the ORM object.
    Cleaned up after the test.
    """
    db = SessionLocal()
    entity = DetectedEntity(
        media_id=media_id,
        tracking_id="track-001",
        entity_type="face",
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    yield entity
    db.delete(entity)
    db.commit()
    db.close()


@pytest.fixture()
def seeded_detection(seeded_entity: DetectedEntity) -> Detection:
    """
    Seed a Detection row for the seeded entity.
    Cleaned up after the test.
    """
    db = SessionLocal()
    detection = Detection(
        entity_id=seeded_entity.entity_id,
        frame_number=42,
        confidence=0.95,
        timestamp=1.4,
        bbox_x=10.0,
        bbox_y=20.0,
        bbox_width=50.0,
        bbox_height=60.0,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    yield detection
    db.delete(detection)
    db.commit()
    db.close()


@pytest.fixture()
def seeded_processed(media_id: int) -> ProcessedMedia:
    """
    Seed a ProcessedMedia row for the given media_id.
    Cleaned up after the test.
    """
    db = SessionLocal()
    processed = ProcessedMedia(
        media_id=media_id,
        output_path="outputs/result_test.mp4",
        output_type="protected_video",
    )
    db.add(processed)
    db.commit()
    db.refresh(processed)
    yield processed
    db.delete(processed)
    db.commit()
    db.close()


@pytest.fixture()
def seeded_selection(seeded_entity: DetectedEntity, seeded_processed: ProcessedMedia) -> SelectedObject:
    """
    Seed a SelectedObject linking the entity to the processed media.
    Cleaned up after the test.
    """
    db = SessionLocal()
    selection = SelectedObject(
        object_id=seeded_entity.entity_id,
        processed_id=seeded_processed.processed_id,
        concealing_type="blur",
        intensity=30.0,
    )
    db.add(selection)
    db.commit()
    db.refresh(selection)
    yield selection
    db.delete(selection)
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Tests: Detected Entities
# ---------------------------------------------------------------------------


def test_list_entities_for_media_empty(media_id: int):
    """
    Test 1: GET /api/results/media/{media_id}/entities on a video with no entities.
    Expect HTTP 200 with total=0 and empty items list.
    """
    resp = client.get(f"/api/results/media/{media_id}/entities")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_entities_for_media_with_data(media_id: int, seeded_entity: DetectedEntity):
    """
    Test 2: GET /api/results/media/{media_id}/entities with one seeded entity.
    Expect HTTP 200, total=1, correct entity fields.
    """
    resp = client.get(f"/api/results/media/{media_id}/entities")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["entity_id"] == seeded_entity.entity_id
    assert item["media_id"] == media_id
    assert item["tracking_id"] == "track-001"
    assert item["entity_type"] == "face"


def test_list_entities_for_nonexistent_media():
    """
    Test 3: GET /api/results/media/{media_id}/entities with non-existent media_id.
    Expect HTTP 404.
    """
    resp = client.get("/api/results/media/999999/entities")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_list_entities_pagination(media_id: int):
    """
    Test 4: Pagination (skip, limit) works for entity listing.
    """
    db = SessionLocal()
    entities = []
    for i in range(3):
        e = DetectedEntity(media_id=media_id, tracking_id=f"track-{i}", entity_type="face")
        db.add(e)
        db.commit()
        db.refresh(e)
        entities.append(e)

    try:
        resp_all = client.get(f"/api/results/media/{media_id}/entities?limit=200")
        total = resp_all.json()["total"]
        assert total >= 3

        resp_one = client.get(f"/api/results/media/{media_id}/entities?skip=0&limit=1")
        assert resp_one.status_code == 200
        assert len(resp_one.json()["items"]) == 1
        assert resp_one.json()["total"] == total
    finally:
        for e in entities:
            db.delete(e)
        db.commit()
        db.close()


def test_get_entity_by_id_success(seeded_entity: DetectedEntity):
    """
    Test 5: GET /api/results/entities/{entity_id} returns correct entity.
    """
    resp = client.get(f"/api/results/entities/{seeded_entity.entity_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["entity_id"] == seeded_entity.entity_id
    assert data["tracking_id"] == "track-001"
    assert data["entity_type"] == "face"


def test_get_entity_by_id_not_found():
    """
    Test 6: GET /api/results/entities/{entity_id} with unknown ID → HTTP 404.
    """
    resp = client.get("/api/results/entities/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: Detections
# ---------------------------------------------------------------------------


def test_list_detections_for_entity_empty(seeded_entity: DetectedEntity):
    """
    Test 7: GET /api/results/entities/{entity_id}/detections with no detection data.
    Expect HTTP 200, total=0, empty list.
    """
    resp = client.get(f"/api/results/entities/{seeded_entity.entity_id}/detections")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_detections_for_entity_with_data(
    seeded_entity: DetectedEntity, seeded_detection: Detection
):
    """
    Test 8: GET /api/results/entities/{entity_id}/detections with one seeded detection.
    Expect HTTP 200, total=1, correct bounding-box fields.
    """
    resp = client.get(f"/api/results/entities/{seeded_entity.entity_id}/detections")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["detection_id"] == seeded_detection.detection_id
    assert item["entity_id"] == seeded_entity.entity_id
    assert item["frame_number"] == 42
    assert item["confidence"] == pytest.approx(0.95)
    assert item["bbox_x"] == pytest.approx(10.0)
    assert item["bbox_width"] == pytest.approx(50.0)


def test_list_detections_for_nonexistent_entity():
    """
    Test 9: GET detections for non-existent entity → HTTP 404.
    """
    resp = client.get("/api/results/entities/999999/detections")
    assert resp.status_code == 404, resp.text


def test_get_detection_by_id_success(seeded_detection: Detection):
    """
    Test 10: GET /api/results/detections/{detection_id} returns correct detection.
    """
    resp = client.get(f"/api/results/detections/{seeded_detection.detection_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["detection_id"] == seeded_detection.detection_id
    assert data["frame_number"] == 42
    assert data["timestamp"] == pytest.approx(1.4)
    assert data["bbox_height"] == pytest.approx(60.0)


def test_get_detection_by_id_not_found():
    """
    Test 11: GET /api/results/detections/999999 → HTTP 404.
    """
    resp = client.get("/api/results/detections/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: Processed Media
# ---------------------------------------------------------------------------


def test_list_processed_for_media_empty(media_id: int):
    """
    Test 12: GET /api/results/media/{media_id}/processed with no processed outputs.
    Expect HTTP 200, total=0, empty list.
    """
    resp = client.get(f"/api/results/media/{media_id}/processed")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_processed_for_media_with_data(media_id: int, seeded_processed: ProcessedMedia):
    """
    Test 13: GET /api/results/media/{media_id}/processed with one seeded output.
    """
    resp = client.get(f"/api/results/media/{media_id}/processed")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["processed_id"] == seeded_processed.processed_id
    assert item["media_id"] == media_id
    assert item["output_path"] == "outputs/result_test.mp4"
    assert item["output_type"] == "protected_video"


def test_list_processed_for_nonexistent_media():
    """
    Test 14: GET /api/results/media/999999/processed → HTTP 404.
    """
    resp = client.get("/api/results/media/999999/processed")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_get_processed_by_id_success(seeded_processed: ProcessedMedia):
    """
    Test 15: GET /api/results/processed/{processed_id} returns correct record.
    """
    resp = client.get(f"/api/results/processed/{seeded_processed.processed_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["processed_id"] == seeded_processed.processed_id
    assert data["output_type"] == "protected_video"


def test_get_processed_by_id_not_found():
    """
    Test 16: GET /api/results/processed/999999 → HTTP 404.
    """
    resp = client.get("/api/results/processed/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: Selected Objects
# ---------------------------------------------------------------------------


def test_list_selections_for_processed_empty(seeded_processed: ProcessedMedia):
    """
    Test 17: GET /api/results/processed/{processed_id}/selections with no selections.
    Expect HTTP 200, total=0.
    """
    resp = client.get(f"/api/results/processed/{seeded_processed.processed_id}/selections")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_selections_for_processed_with_data(
    seeded_processed: ProcessedMedia, seeded_selection: SelectedObject
):
    """
    Test 18: GET /api/results/processed/{processed_id}/selections with one seeded selection.
    """
    resp = client.get(f"/api/results/processed/{seeded_processed.processed_id}/selections")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["selection_id"] == seeded_selection.selection_id
    assert item["processed_id"] == seeded_processed.processed_id
    assert item["concealing_type"] == "blur"
    assert item["intensity"] == pytest.approx(30.0)


def test_list_selections_for_nonexistent_processed():
    """
    Test 19: GET /api/results/processed/999999/selections → HTTP 404.
    """
    resp = client.get("/api/results/processed/999999/selections")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


def test_get_selection_by_id_success(seeded_selection: SelectedObject):
    """
    Test 20: GET /api/results/selections/{selection_id} returns correct record.
    """
    resp = client.get(f"/api/results/selections/{seeded_selection.selection_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["selection_id"] == seeded_selection.selection_id
    assert data["concealing_type"] == "blur"
    assert data["intensity"] == pytest.approx(30.0)


def test_get_selection_by_id_not_found():
    """
    Test 21: GET /api/results/selections/999999 → HTTP 404.
    """
    resp = client.get("/api/results/selections/999999")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()

