"""
Tests for the official FYP SQLAlchemy database models and relationships:
- User
- Media
- PROCESSED_MEDIA
- DETECTED_ENTITY
- DETECTION
- SELECTED_OBJECT
"""

import uuid
import pytest
from sqlalchemy.orm import Session
from app.database import SessionLocal, ensure_default_user
from app.models.detected_entity import DetectedEntity
from app.models.detection import Detection
from app.models.media import Media
from app.models.processed_media import ProcessedMedia
from app.models.selected_object import SelectedObject
from app.models.user import User
from app.schemas.media import MediaResponse


@pytest.fixture
def db_session():
    """Provides a transactional database session for tests."""
    ensure_default_user()
    session: Session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def test_user_and_media_models(db_session: Session):
    """Verify User and Media model creation and foreign key relationship."""
    unique_user_id = 9999
    user = User(user_id=unique_user_id)
    db_session.add(user)
    db_session.commit()

    try:
        media = Media(
            user_id=user.user_id,
            file_name="drone_footage.mp4",
            file_path="uploads/drone_footage.mp4",
            duration_seconds=45.2,
            fps=60.0,
        )
        db_session.add(media)
        db_session.commit()
        db_session.refresh(media)

        assert media.media_id is not None
        assert media.user_id == unique_user_id
        assert media.file_name == "drone_footage.mp4"
        assert media.duration_seconds == 45.2

        # Test Pydantic schema validation
        schema = MediaResponse.model_validate(media)
        assert schema.media_id == media.media_id
        assert schema.user_id == unique_user_id
    finally:
        db_session.delete(user)
        db_session.commit()


def test_full_detection_and_processing_workflow(db_session: Session):
    """
    Verify complete relational workflow:
    User -> Media -> DETECTED_ENTITY -> DETECTION
    User -> Media -> PROCESSED_MEDIA -> SELECTED_OBJECT
    """
    user = db_session.query(User).filter(User.user_id == 1).first()
    if not user:
        user = User(user_id=1)
        db_session.add(user)
        db_session.commit()

    # 1. Media
    media = Media(
        user_id=1,
        file_name="traffic_junction.mp4",
        file_path="uploads/traffic_junction.mp4",
        duration_seconds=10.0,
        fps=30.0,
    )
    db_session.add(media)
    db_session.commit()
    db_session.refresh(media)

    try:
        # 2. Detected Entity
        entity = DetectedEntity(
            media_id=media.media_id,
            tracking_id="person_01",
            entity_type="face",
        )
        db_session.add(entity)
        db_session.commit()
        db_session.refresh(entity)
        assert entity.entity_id is not None

        # 3. Detection (frame bounding box)
        detection = Detection(
            entity_id=entity.entity_id,
            frame_number=1,
            confidence=0.95,
            timestamp=0.033,
            bbox_x=100.0,
            bbox_y=150.0,
            bbox_width=50.0,
            bbox_height=60.0,
        )
        db_session.add(detection)
        db_session.commit()
        db_session.refresh(detection)
        assert detection.detection_id is not None
        assert detection.confidence == 0.95

        # 4. Processed Media
        processed = ProcessedMedia(
            media_id=media.media_id,
            output_path="outputs/traffic_junction_blurred.mp4",
            output_type="video/mp4",
        )
        db_session.add(processed)
        db_session.commit()
        db_session.refresh(processed)
        assert processed.processed_id is not None

        # 5. Selected Object
        selected = SelectedObject(
            object_id=entity.entity_id,
            processed_id=processed.processed_id,
            concealing_type="blur",
            intensity=35.0,
        )
        db_session.add(selected)
        db_session.commit()
        db_session.refresh(selected)
        assert selected.selection_id is not None
        assert selected.concealing_type == "blur"
        assert selected.intensity == 35.0

    finally:
        # Cascade deletion from Media should clean up child entities
        db_session.delete(media)
        db_session.commit()
