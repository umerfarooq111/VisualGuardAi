"""
Unit tests for Backend Configuration Management.
"""

from pathlib import Path
from app.config import BASE_DIR, Settings, settings


def test_settings_singleton_loaded():
    """Verify that settings instance is loaded with valid defaults."""
    assert settings.APP_NAME == "VisualGuard AI Backend"
    assert settings.APP_VERSION == "1.0.0"
    assert settings.ENVIRONMENT in ("development", "production", "testing")
    assert isinstance(settings.DEBUG, bool)
    assert isinstance(settings.HOST, str)
    assert isinstance(settings.PORT, int)


def test_database_url_placeholder():
    """Verify the database URL is loaded as a string placeholder."""
    assert isinstance(settings.DATABASE_URL, str)
    assert "postgresql" in settings.DATABASE_URL
    assert "visualguard_db" in settings.DATABASE_URL


def test_storage_paths_are_pathlib_paths():
    """Verify that storage paths are pathlib.Path instances and absolute."""
    assert isinstance(settings.UPLOAD_DIR, Path)
    assert isinstance(settings.OUTPUT_DIR, Path)
    assert settings.UPLOAD_DIR.is_absolute()
    assert settings.OUTPUT_DIR.is_absolute()


def test_storage_directories_exist():
    """Verify that ensure_storage_directories creates the required folders."""
    settings.ensure_storage_directories()
    assert settings.UPLOAD_DIR.exists()
    assert settings.OUTPUT_DIR.exists()
    assert settings.UPLOAD_DIR.is_dir()
    assert settings.OUTPUT_DIR.is_dir()


def test_custom_settings_override():
    """Verify that Settings can be instantiated with custom values."""
    custom = Settings(
        APP_NAME="VisualGuard Test Suite",
        APP_VERSION="2.0.0",
        ENVIRONMENT="testing",
        UPLOAD_DIR="custom_uploads",
        OUTPUT_DIR="custom_outputs",
    )
    assert custom.APP_NAME == "VisualGuard Test Suite"
    assert custom.APP_VERSION == "2.0.0"
    assert custom.ENVIRONMENT == "testing"
    assert custom.UPLOAD_DIR == (BASE_DIR / "custom_uploads").resolve()
    assert custom.OUTPUT_DIR == (BASE_DIR / "custom_outputs").resolve()

