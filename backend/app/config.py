"""
VisualGuard AI - Backend Configuration Management
=================================================

This module defines the configuration settings for the VisualGuard AI backend
using Pydantic Settings. It automatically loads variables from environment
variables or a local `.env` file, with sensible fallback defaults.
"""

from pathlib import Path
from typing import Literal, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the backend (absolute path to the 'backend' folder)
BASE_DIR: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application configuration settings.

    Reads environment variables from the OS or a .env file located at
    the root of the backend folder. Sensible defaults are provided for
    all optional fields.
    """

    # 1. Application Name & Version
    APP_NAME: str = Field(
        default="VisualGuard AI Backend",
        description="Human-readable name of the application.",
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Semantic version of the backend application.",
    )

    # 2. Environment
    ENVIRONMENT: Literal["development", "production", "testing"] = Field(
        default="development",
        description="Application runtime environment: development, production, or testing.",
    )

    # 3. Server Networking (Optional with defaults)
    DEBUG: bool = Field(
        default=True,
        description="Debug mode toggle. Set to False in production.",
    )
    HOST: str = Field(
        default="127.0.0.1",
        description="Host interface for the application server.",
    )
    PORT: int = Field(
        default=8000,
        description="Port on which the application server listens.",
    )

    # 4. Database Connection URL (Placeholder - no active connection in this phase)
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/visualguard_db",
        description="Placeholder PostgreSQL connection URL for upcoming database integration.",
    )

    # 5. Storage Directories (configured using pathlib.Path)
    UPLOAD_DIR: Path = Field(
        default=BASE_DIR / "uploads",
        description="Directory for temporary storage of uploaded media files.",
    )
    OUTPUT_DIR: Path = Field(
        default=BASE_DIR / "outputs",
        description="Directory for storing processed privacy-protected media outputs.",
    )

    # 6. File Upload Limits
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=100,
        description="Maximum allowed video upload size in Megabytes.",
    )

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the maximum allowed upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @field_validator("UPLOAD_DIR", "OUTPUT_DIR", mode="before")
    @classmethod
    def resolve_storage_path(cls, value: Union[str, Path]) -> Path:
        """
        Convert string paths to Path objects and resolve relative paths
        against the backend base directory.
        """
        path = Path(value)
        if not path.is_absolute():
            return (BASE_DIR / path).resolve()
        return path.resolve()

    def ensure_storage_directories(self) -> None:
        """
        Create upload and output directories if they do not already exist.
        """
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instantiate a singleton settings object for application-wide use
settings: Settings = Settings()

# Ensure directories exist upon module initialization
settings.ensure_storage_directories()
